import os
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from web3 import Web3
from eth_abi import decode_abi
from dotenv import load_dotenv
from flask import Flask, jsonify
import pinatapy
import signal
import sys
from fetch_prices import update_price_data
import json
from bisect import bisect_left
from eth_utils import to_checksum_address
import asyncio
from decimal import Decimal
from flask_cors import CORS


# Set up logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

file_handler = RotatingFileHandler('app.log', maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

# Environment variables
INFURA_KEY = os.getenv("INFURA_KEY")
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")
TOTAL_REWARDS = float(os.getenv("TOTAL_REWARDS"))
START_DATE = datetime.fromisoformat(os.getenv("START_DATE"))
PROGRAM_DURATION_WEEKS = int(os.getenv("PROGRAM_DURATION_WEEKS"))
START_BLOCK = int(os.getenv("START_BLOCK"))

# Connect to Arbitrum using Alchemy
infura_url = f"https://arbitrum-mainnet.infura.io/v3/{INFURA_KEY}"
w3 = Web3(Web3.HTTPProvider(infura_url))

if w3.isConnected():
    logger.info("Successfully connected to Arbitrum network")
else:
    logger.error("Failed to connect to Arbitrum network")
    sys.exit(1)

def load_abi(filename):
    """
    Load the ABI (Application Binary Interface) file from the given filename.
    This function reads the ABI file from the './abi' directory and parses it as JSON.

    :param filename: Name of the ABI file to load.
    :return: Parsed ABI JSON.
    :raises FileNotFoundError: If the ABI file is not found.
    """    
    try:
        with open(f"./abi/{filename}", 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"ABI file not found: {filename}")
        raise

CURVE_ABI = load_abi("curve_abi.json")
UNIV3_ABI = load_abi("univ3_abi.json")

def to_checksum_address(address):
    """
    Convert an Ethereum address to its checksummed version.

    :param address: Ethereum address in string format.
    :return: Checksummed Ethereum address.
    """    
    return Web3.toChecksumAddress(address)

# Pool addresses and configurations dictionary
POOLS = [
    {"address": to_checksum_address("0x186cf879186986a20aadfb7ead50e3c20cb26cec"), "abi": CURVE_ABI, "tokens": [{"tbtc": "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40"}, {"wrapped-bitcoin": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"}]},
    {"address": to_checksum_address("0xe9e6b9aaafaf6816c3364345f6ef745ccfc8660a"), "abi": UNIV3_ABI, "tokens": [{"tbtc": "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40"}, {"wrapped-bitcoin": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"}]},
    {"address": to_checksum_address("0xCb198a55e2a88841E855bE4EAcaad99422416b33"), "abi": UNIV3_ABI, "tokens": [{"tbtc": "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40"}, {"ethereum": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"}]}
]

# Load historical prices once at the start of the script
with open('token_historical_prices.json', 'r') as f:
    HISTORICAL_PRICES = json.load(f)

# Program dates and block heights
END_DATE = START_DATE + timedelta(weeks=PROGRAM_DURATION_WEEKS)
logger.info(f"Program end date: {END_DATE}")

# Convert dates to Unix timestamps
START_TIMESTAMP = int(START_DATE.timestamp())
END_TIMESTAMP = int(END_DATE.timestamp())

# Initialize Pinata client
pinata = pinatapy.PinataPy(PINATA_API_KEY, PINATA_SECRET_API_KEY)

# Flask app for API
app = Flask(__name__)
CORS(app)

# File to store latest CIDs and last processed block
STATE_FILE = 'program_state.json'

def save_state(last_block, events_cid, rewards_cid):
    """
    Save the current state of the program to a JSON file.
    This function writes the last processed block number and the latest IPFS CIDs for events and rewards to a file.

    :param last_block: The last processed block number.
    :param events_cid: The IPFS CID for the latest events.
    :param rewards_cid: The IPFS CID for the latest rewards.
    """    
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'last_processed_block': last_block,
            'events_cid': events_cid,
            'rewards_cid': rewards_cid
        }, f)
    logger.info(f"State saved. Last processed block: {last_block}")

def load_state():
    """
    Load the saved state of the program from a JSON file.
    This function reads the last processed block number and the latest IPFS CIDs for events and rewards from a file.

    :return: A dictionary containing the last processed block number, and the latest IPFS CIDs for events and rewards.
    """    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        logger.info(f"State loaded. Last processed block: {state['last_processed_block']}")
        return state
    except FileNotFoundError:
        logger.info(f"No state file found. Starting from block {START_BLOCK}")
        return {'last_processed_block': START_BLOCK, 'events_cid': None, 'rewards_cid': None}

class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for handling Decimal objects.
    This encoder converts Decimal objects to their string representation when encoding JSON.
    """    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return format(obj, 'f')
        return super(CustomJSONEncoder, self).default(obj)
    
def decimal_to_str(obj):
    """
    Recursively convert all Decimal objects in the given object to their string representation.
    This function handles nested structures like lists and dictionaries.

    :param obj: The object to convert.
    :return: The object with all Decimal objects converted to strings.
    """    
    if isinstance(obj, Decimal):
        return format(obj, 'f')
    elif isinstance(obj, dict):
        return {k: decimal_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_str(v) for v in obj]
    return obj

def fetch_token_price(token_name, date):
    """
    Fetch the historical price of a token for a specific date.
    This function retrieves the price of the given token from the preloaded historical prices data.

    :param token_name: The name of the token.
    :param date: The date for which to fetch the token price.
    :return: The price of the token at the specified date.
    """    
    if not token_name or token_name not in HISTORICAL_PRICES:
        logger.error(f"Unknown token or no price data: {token_name}")
        return 0

    target_timestamp = int(date.timestamp() * 1000)  # Convert to milliseconds
    price_data = HISTORICAL_PRICES[token_name]
    
    # Find the index of the closest timestamp
    timestamps = [entry[0] for entry in price_data]
    index = bisect_left(timestamps, target_timestamp)
    
    if index == 0:
        closest_price = price_data[0][1]
    elif index == len(price_data):
        closest_price = price_data[-1][1]
    else:
        before = price_data[index - 1]
        after = price_data[index]
        if target_timestamp - before[0] < after[0] - target_timestamp:
            closest_price = before[1]
        else:
            closest_price = after[1]
    return closest_price

def get_event_abi(contract, event_name):
    """
    Retrieve the ABI definition for a specific event from a contract's ABI.

    :param contract: The contract object.
    :param event_name: The name of the event.
    :return: The ABI definition for the event, or None if the event is not found.
    """    
    for item in contract.abi:
        if item['type'] == 'event' and item['name'] == event_name:
            return item
    return None

def create_event_signature(event_abi):
    """
    Create the signature for an event using its ABI definition.

    :param event_abi: The ABI definition of the event.
    :return: The event signature string, or None if the event ABI is not provided.
    """    
    if not event_abi:
        return None
    types = ','.join([input['type'] for input in event_abi['inputs']])
    return f"{event_abi['name']}({types})"

def decode_log(abi, log):
    """
    Decode a log entry using the given ABI definition.

    :param abi: The ABI definition of the event.
    :param log: The log entry to decode.
    :return: A dictionary containing the decoded event data.
    """    
    topics = log['topics']
    if len(topics) > 0:
        topics = topics[1:]  # remove event signature
    
    indexed_inputs = [input for input in abi['inputs'] if input['indexed']]
    non_indexed_inputs = [input for input in abi['inputs'] if not input['indexed']]
    
    decoded = decode_abi([input['type'] for input in non_indexed_inputs], bytes.fromhex(log['data'][2:]))
    
    event = {'event': abi['name'], 'args': {}}
    for i, input in enumerate(indexed_inputs):
        event['args'][input['name']] = topics[i]
    for i, input in enumerate(non_indexed_inputs):
        event['args'][input['name']] = decoded[i]
    
    return event

def fetch_events(w3, pool, from_block, to_block, start_timestamp, end_timestamp):
    """
    Fetch and decode events from a blockchain pool within a specified block range and time period.

    :param w3: Web3 instance connected to the blockchain.
    :param pool: Dictionary containing pool address, ABI, and token configurations.
    :param from_block: Starting block number for fetching events.
    :param to_block: Ending block number for fetching events.
    :param start_timestamp: Starting Unix timestamp for filtering events.
    :param end_timestamp: Ending Unix timestamp for filtering events.
    :return: List of decoded events.
    """    
    contract = w3.eth.contract(address=pool["address"], abi=pool["abi"])
    all_events = []
    try:
        if pool["abi"] == CURVE_ABI:
            event_names = ["AddLiquidity", "RemoveLiquidity", "RemoveLiquidityOne", "RemoveLiquidityImbalance"]
        elif pool["abi"] == UNIV3_ABI:
            event_names = ["Burn", "Mint"]
        else:
            logger.error(f"Unknown ABI for pool {pool['address']}")
            return []

        token1, token2 = get_tokens_from_contract(pool)                

        for event_name in event_names:
            event_abi = get_event_abi(contract, event_name)
            if not event_abi:
                logger.warning(f"Event {event_name} not found in ABI for pool {pool['address']}")
                continue

            event_signature = create_event_signature(event_abi)
            if not event_signature:
                logger.warning(f"Could not create signature for event {event_name}")
                continue

            event_signature_hash = Web3.keccak(text=event_signature).hex()
            logs = w3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': to_block,
                'address': pool["address"],
                'topics': [event_signature_hash]
            })

            logger.info(f"Fetched {len(logs)} {event_name} events for pool {pool['address']}")
            
            for log in logs:
                try:
                    block = w3.eth.get_block(log['blockNumber'])
                    event_timestamp = block['timestamp']
                    if start_timestamp <= event_timestamp <= end_timestamp:
                        decoded_event = decode_log(event_abi, log)
                        decoded_event['timestamp'] = event_timestamp
                        decoded_event['transactionHash'] = log['transactionHash'].hex()
                        decoded_event['tokens'] = {"token1": token1, "token2": token2}
                        all_events.append(decoded_event)
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to fetch events for pool {pool['address']}: {str(e)}")

    logger.info(f"Total events elegible for pool {pool['address']}: {len(all_events)}")
    return all_events

def get_token_name_by_address(address, pool):
    """
    Retrieve the token name by its address from the pool configuration.

    :param address: Token contract address.
    :param pool: Pool configuration dictionary.
    :return: Token name or None if not found.
    """    
    for token in pool['tokens']:
        if isinstance(token, dict):
            for name, addr in token.items():
                if addr.lower() == address.lower():
                    return name
    return None

def get_tokens_from_contract(pool):
    """
    Get the names of the tokens associated with a pool contract.

    :param pool: Pool configuration dictionary.
    :return: Tuple containing the names of the two tokens.
    """    
    contract = w3.eth.contract(address=pool["address"], abi=pool["abi"])
    try:
        if hasattr(contract.functions, 'token0') and hasattr(contract.functions, 'token1'):
            token0_address = contract.functions.token0().call()
            token1_address = contract.functions.token1().call()
            token0_name = get_token_name_by_address(token0_address, pool)
            token1_name = get_token_name_by_address(token1_address, pool)
            return token0_name, token1_name
        elif hasattr(contract.functions, 'coins'):
            coin0_address = contract.functions.coins(0).call()
            coin1_address = contract.functions.coins(1).call()
            coin0_name = get_token_name_by_address(coin0_address, pool)
            coin1_name = get_token_name_by_address(coin1_address, pool)
            return coin0_name, coin1_name
    except Exception as e:
        logger.error(f"Error fetching token addresses from contract: {str(e)}")
        return None, None
    return None, None

def calculate_rewards(events):
    """
    Calculate rewards for liquidity providers based on their activity.

    :param events: List of decoded events.
    :return: List of rewards for each liquidity provider.
    """    
    provider_liquidity = {}
    end_timestamp = datetime.now()

    sorted_events = sorted(events, key=lambda x: x['timestamp'])
    
    for event in sorted_events:
        try:
            provider = event['args']['provider'] if 'provider' in event['args'] else event['args'].get('owner')
            if not provider:
                logger.warning(f"No provider found for event: {event}")
                continue

            timestamp = datetime.fromtimestamp(event['timestamp'])
            event_type = event['event']
            tokens = event['tokens']

            if event_type in ["AddLiquidity", "Mint"]:
                action = "add"
                if event_type == "AddLiquidity":
                    amounts = list(event['args'].get('token_amounts', []))
                    # Ensure we have two values, add 0 if necessary
                    amounts = amounts + [0] * (2 - len(amounts))
                else:  # Mint event
                    amounts = [event['args'].get('amount0', 0), event['args'].get('amount1', 0)]
            elif event_type in ["RemoveLiquidity", "RemoveLiquidityOne", "RemoveLiquidityImbalance", "Burn"]:
                action = "remove"
                if event_type in ["RemoveLiquidity", "RemoveLiquidityImbalance"]:
                    amounts = list(event['args'].get('token_amounts', []))
                    # Ensure we have two values, add 0 if necessary
                    amounts = amounts + [0] * (2 - len(amounts))
                elif event_type == "RemoveLiquidityOne":
                    amounts = [event['args'].get('token_amount', 0), 0]
                else:  # Burn event
                    amounts = [event['args'].get('amount0', 0), event['args'].get('amount1', 0)]
            else:
                logger.warning(f"Unknown event type: {event_type}")
                continue

            if len(amounts) < 2:
                logger.warning(f"Invalid amounts for event: {event}")
                continue

            token1_price = fetch_token_price(tokens.get('token1'), timestamp)
            token2_price = fetch_token_price(tokens.get('token2'), timestamp)

            total_value = (float(amounts[0]) * token1_price) + (float(amounts[1]) * token2_price)

            if provider not in provider_liquidity:
                provider_liquidity[provider] = []

            if action == "add":
                if provider_liquidity[provider]:
                    last_event = provider_liquidity[provider][-1]
                    new_amount = last_event[1] + total_value
                else:
                    new_amount = total_value
                provider_liquidity[provider].append((timestamp, new_amount))
            elif action == "remove":
                if provider_liquidity[provider]:
                    last_event = provider_liquidity[provider][-1]
                    new_amount = max(0, last_event[1] - total_value)
                    provider_liquidity[provider].append((timestamp, new_amount))
            
            # logger.info(f"Processed {action} event for provider {normalize_address(provider)}: {total_value}")
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}", exc_info=True)

    weighted_avg_liquidity = {}
    for provider, liquidity_events in provider_liquidity.items():
        if not liquidity_events:
            logger.warning(f"No liquidity events for address {normalize_address(provider)}")
            continue

        total_liquidity_time = 0
        for i in range(len(liquidity_events)):
            current_time, current_amount = liquidity_events[i]
            
            if i < len(liquidity_events) - 1:
                next_time = liquidity_events[i+1][0]
            else:
                next_time = end_timestamp

            duration = (next_time - current_time).total_seconds()
            total_liquidity_time += current_amount * duration

        start_time = liquidity_events[0][0]
        total_duration = (end_timestamp - start_time).total_seconds()
        
        if total_duration > 0:
            weighted_avg_liquidity[provider] = total_liquidity_time / total_duration
        else:
            logger.warning(f"Zero duration for provider {provider}")
            weighted_avg_liquidity[provider] = 0

    total_weighted_liquidity = sum(weighted_avg_liquidity.values())
    rewards = []
    
    if total_weighted_liquidity > 0:
        for provider, avg_liquidity in weighted_avg_liquidity.items():
            provider_reward = (avg_liquidity / total_weighted_liquidity) * TOTAL_REWARDS
            rewards.append({
                "provider": provider.hex() if isinstance(provider, bytes) else provider,
                "weighted_avg_liquidity": avg_liquidity,
                "estimated_reward": provider_reward
            })
    else:
        logger.warning("Total weighted liquidity is zero, no rewards to distribute")

    return rewards

def is_contract(w3, address):
    """
    Check if the given address is a smart contract.

    :param w3: Web3 instance connected to the blockchain.
    :param address: Ethereum address to check.
    :return: True if the address is a contract, False otherwise.
    """
    code = w3.eth.get_code(address)
    return len(code) > 0

def normalize_address(address):
    """
    Normalize an Ethereum address to its checksummed version.
    This function handles both string and bytes input formats.

    :param address: Ethereum address to normalize.
    :return: Checksummed Ethereum address.
    """    
    # Convert bytes to hex string if address is of bytes type
    if isinstance(address, bytes):
        address = address.hex()
    elif not isinstance(address, str):
        raise ValueError(f"Unsupported address format: {type(address)}")

    # Common processing steps for both bytes and str types
    address = address.lower().removeprefix('0x').lstrip('0').zfill(40)
    address = '0x' + address
    
    return to_checksum_address(address)

def log_to_ipfs(w3, new_events, rewards):
    """
    Log events and rewards to IPFS using Pinata.

    :param w3: Web3 instance connected to the blockchain.
    :param new_events: List of new events to log.
    :param rewards: List of calculated rewards to log.
    :return: Tuple containing the IPFS CIDs for the logged events and rewards.
    """    
    try:
        logger.info(f"Logging {len(new_events)} new events to IPFS")

        formatted_events = []
        for event in new_events:
            event_type = event['event'].lower()
            provider = event['args'].get('provider') or event['args'].get('owner')
            tokens = event['tokens']

            # Normalize and convert provider to checksum address
            try:
                provider = normalize_address(provider)
            except Exception as e:
                logger.error(f"Error normalizing address: {str(e)}", exc_info=True)
                continue

            formatted_event = {
                "event": "add" if event_type in ["addliquidity", "mint"] else "remove",
                "provider": provider,
                "providerType": "contract" if is_contract(w3, provider) else "wallet",
                "tokens": {
                    "token1": tokens.get('token1'),
                    "token2": tokens.get('token2')
                },
                "token_amounts": {},
                "timestamp": event['timestamp'],
                "transactionHash": event['transactionHash']
            }

            if event_type in ["addliquidity", "removeliquidity", "removeliquidityimbalance"]:
                amounts = event['args'].get('token_amounts', [])
                formatted_event["token_amounts"]["token1"] = amounts[0] if len(amounts) > 0 else '0'
                formatted_event["token_amounts"]["token2"] = amounts[1] if len(amounts) > 1 else '0'
            elif event_type == "removeliquidityone":
                formatted_event["token_amounts"]["token1"] = event['args'].get('token_amount', 0)
                formatted_event["token_amounts"]["token2"] = '0'
            elif event_type in ["mint", "burn"]:
                # For UniswapV3, we need to match the token order with the pool's token order
                formatted_event["token_amounts"]["token1"] = event['args'].get('amount0', 0)
                formatted_event["token_amounts"]["token2"] = event['args'].get('amount1', 0)

            formatted_events.append(formatted_event)
            time.sleep(0.1)

        events_json = {"events": formatted_events}
        
        # Format rewards
        formatted_rewards = []
        for reward in rewards:
            provider = normalize_address(reward['provider'])
            
            formatted_rewards.append({
                "provider": provider,
                "weighted_avg_liquidity": format(Decimal(str(reward['weighted_avg_liquidity'])), 'f'),
                "estimated_reward": format(Decimal(str(reward['estimated_reward'])), 'f')
            })
        
        rewards_json = {
            "overall_weighted_avg_liquidity": format(Decimal(str(sum(Decimal(str(r["weighted_avg_liquidity"])) for r in rewards))), 'f'),
            "rewards": formatted_rewards
        }

        # Convert all Decimal objects to strings
        events_json = decimal_to_str(events_json)
        rewards_json = decimal_to_str(rewards_json)

        # Pin JSON data to IPFS
        events_response = pinata.pin_json_to_ipfs(events_json)
        rewards_response = pinata.pin_json_to_ipfs(rewards_json)
        
        # Extract CIDs from response
        new_events_cid = events_response.get('IpfsHash')
        new_rewards_cid = rewards_response.get('IpfsHash')

        if not new_events_cid or not new_rewards_cid:
            raise ValueError("Failed to extract IPFS hash from Pinata response")

        logger.info(f"New events pinned to IPFS with CID: {new_events_cid}")
        logger.info(f"New rewards pinned to IPFS with CID: {new_rewards_cid}")
        
        return new_events_cid, new_rewards_cid
    except Exception as e:
        logger.error(f"Error logging to IPFS: {str(e)}", exc_info=True)
        raise

@app.route('/api/latest-cids', methods=['GET'])
def get_latest_cids():
    """
    API endpoint to get the latest IPFS CIDs for events and rewards.

    :return: JSON response containing the latest IPFS CIDs.
    """    
    state = load_state()
    logger.info(f"API request for latest CIDs. Returning: {state['events_cid']}, {state['rewards_cid']}")
    return jsonify({
        'events_cid': state['events_cid'],
        'rewards_cid': state['rewards_cid']
    }), 200

def signal_handler(sig, frame):
    """
    Handle shutdown signals to gracefully exit the application.

    :param sig: Signal number.
    :param frame: Current stack frame.
    """    
    logger.info("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    """
    Main function to run the rewards calculation and logging loop.
    This function periodically updates price data, fetches events, calculates rewards, logs data to IPFS, and saves the program state.
    """    
    while datetime.now() <= END_DATE + timedelta(days=1):
        try:
            asyncio.run(update_price_data())
            current_block = w3.eth.get_block('latest')['number']
            logger.info(f"Processing blocks from {START_BLOCK} to {current_block}")
            
            all_events = []
            for pool in POOLS:
                events = fetch_events(w3, pool, START_BLOCK, current_block, START_TIMESTAMP, END_TIMESTAMP)
                all_events.extend(events)

            logger.info(f"Total events elegible: {len(all_events)}")

            if all_events:
                rewards = calculate_rewards(all_events)
                events_cid, rewards_cid = log_to_ipfs(w3, all_events, rewards)
                
                save_state(current_block, events_cid, rewards_cid)
                
                logger.info(f"Events logged to IPFS with CID: {events_cid}")
                logger.info(f"Rewards logged to IPFS with CID: {rewards_cid}")
            else:
                logger.info("No new events in the specified date range.")
        except Exception as e:
            logger.error(f"An error occurred in the main loop: {str(e)}")
            time.sleep(86400)  # Wait for 24 hours before retrying
        
        logger.info(f"Sleeping for 6 hours")
        time.sleep(21600)  # Wait for 6 hours before the next iteration

if __name__ == "__main__":
    # Run the main loop in a separate thread
    import threading
    threading.Thread(target=main, daemon=True).start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)