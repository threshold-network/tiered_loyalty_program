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
from web3.datastructures import AttributeDict
from eth_utils import to_checksum_address, remove_0x_prefix
from hexbytes import HexBytes
import asyncio

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

# Load ABIs from ./abi directory
def load_abi(filename):
    try:
        with open(f"./abi/{filename}", 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"ABI file not found: {filename}")
        raise

CURVE_ABI = load_abi("curve_abi.json")
UNIV3_ABI = load_abi("univ3_abi.json")

# Token name to CoinGecko ID mapping
TOKEN_TO_COINGECKO_ID = {
    "tbtc": "tbtc",
    "wbtc": "wrapped-bitcoin",
    "eth": "ethereum"
}

def to_checksum_address(address):
    return Web3.toChecksumAddress(address)

# Pool addresses and configurations
POOLS = [
    {"address": to_checksum_address("0x186cf879186986a20aadfb7ead50e3c20cb26cec"), "abi": CURVE_ABI, "tokens": ["tbtc", "wbtc"]},
    # {"address": to_checksum_address("0xe9e6b9aaafaf6816c3364345f6ef745ccfc8660a"), "abi": UNIV3_ABI, "tokens": ["tbtc", "wbtc"]},
    # {"address": to_checksum_address("0xCb198a55e2a88841E855bE4EAcaad99422416b33"), "abi": UNIV3_ABI, "tokens": ["tbtc", "eth"]}
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

# File to store latest CIDs and last processed block
STATE_FILE = 'program_state.json'

def save_state(last_block, events_cid, rewards_cid):
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'last_processed_block': last_block,
            'events_cid': events_cid,
            'rewards_cid': rewards_cid
        }, f)
    logger.info(f"State saved. Last processed block: {last_block}")

def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        logger.info(f"State loaded. Last processed block: {state['last_processed_block']}")
        return state
    except FileNotFoundError:
        logger.info(f"No state file found. Starting from block {START_BLOCK}")
        return {'last_processed_block': START_BLOCK, 'events_cid': None, 'rewards_cid': None}


def serialize_web3_data(obj):
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, AttributeDict):
        return {k: serialize_web3_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_web3_data(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_web3_data(v) for k, v in obj.items()}
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)

# Function to fetch token price
def fetch_token_price(token_name, date):
    token_id = TOKEN_TO_COINGECKO_ID.get(token_name.lower())
    if not token_id or token_id not in HISTORICAL_PRICES:
        logger.error(f"Unknown token or no price data: {token_name}")
        return 0

    target_timestamp = int(date.timestamp() * 1000)  # Convert to milliseconds
    price_data = HISTORICAL_PRICES[token_id]
    
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

    logger.info(f"Found price for {token_name} on {date}: {closest_price}")
    return closest_price

def get_event_abi(contract, event_name):
    for item in contract.abi:
        if item['type'] == 'event' and item['name'] == event_name:
            return item
    return None

def create_event_signature(event_abi):
    if not event_abi:
        return None
    types = ','.join([input['type'] for input in event_abi['inputs']])
    return f"{event_abi['name']}({types})"

def decode_log(abi, log):
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
                        all_events.append(decoded_event)
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to fetch events for pool {pool['address']}: {str(e)}")

    logger.info(f"Total events fetched for pool {pool['address']}: {len(all_events)}")
    return all_events

# Function to calculate rewards based on events
def calculate_rewards(events):
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
            
            if event_type in ["AddLiquidity", "Mint"]:
                action = "add"
                if event_type == "AddLiquidity":
                    amounts = list(event['args'].get('token_amounts', []))
                    # Ensure we have two values, add 0 if necessary
                    amounts = amounts + [0] * (2 - len(amounts))
                    logger.debug(f"AddLiquidity event details: provider={provider}, amounts={amounts}, timestamp={timestamp}")
                else:  # Mint event
                    amounts = [event['args'].get('amount0', 0), event['args'].get('amount1', 0)]
            elif event_type in ["RemoveLiquidity", "RemoveLiquidityOne", "RemoveLiquidityImbalance", "Burn"]:
                action = "remove"
                if event_type in ["RemoveLiquidity", "RemoveLiquidityImbalance"]:
                    amounts = list(event['args'].get('token_amounts', []))
                    # Ensure we have two values, add 0 if necessary
                    amounts = amounts + [0] * (2 - len(amounts))
                elif event_type == "RemoveLiquidityOne":
                    amounts = [event['args'].get('token_amount', 0), 0]  # Assuming it's always the first token
                else:  # Burn event
                    amounts = [event['args'].get('amount0', 0), event['args'].get('amount1', 0)]
            else:
                logger.warning(f"Unknown event type: {event_type}")
                continue

            if len(amounts) < 2:
                logger.warning(f"Invalid amounts for event: {event}")
                continue

            token1_price = fetch_token_price(event['token1'], timestamp)
            token2_price = fetch_token_price(event['token2'], timestamp)

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
            
            logger.info(f"Processed {action} event for provider {provider}: {total_value}")
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}", exc_info=True)

    weighted_avg_liquidity = {}
    for provider, liquidity_events in provider_liquidity.items():
        if not liquidity_events:
            logger.warning(f"No liquidity events for provider {provider}")
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
            logger.info(f"Calculated reward for provider {provider.hex() if isinstance(provider, bytes) else provider}: {provider_reward}")
    else:
        logger.warning("Total weighted liquidity is zero, no rewards to distribute")

    return rewards

def is_contract(w3, address):
    code = w3.eth.get_code(address)
    return len(code) > 0

def normalize_address(address):
    # Convert bytes to hex string if address is of bytes type
    if isinstance(address, bytes):
        address = address.hex()
    elif not isinstance(address, str):
        raise ValueError(f"Unsupported address format: {type(address)}")

    # Common processing steps for both bytes and str types
    address = address.lower().removeprefix('0x').lstrip('0').zfill(40)
    address = '0x' + address
    
    return to_checksum_address(address)

# Function to log events and rewards to IPFS
def log_to_ipfs(w3, new_events, rewards):
    try:
        logger.info(f"Logging {len(new_events)} new events to IPFS")

        formatted_events = []
        for event in new_events:
            event_type = event['event'].lower()
            provider = event['args'].get('provider') or event['args'].get('owner')
            
            logger.debug(f"Original provider address: {provider} (type: {type(provider)})")
            
            # Normalize and convert provider to checksum address
            try:
                provider = normalize_address(provider)
                logger.debug(f"Normalized provider address: {provider}")
            except Exception as e:
                logger.error(f"Error normalizing address: {str(e)}", exc_info=True)
                continue

            formatted_event = {
                "event": "add" if event_type in ["addliquidity", "mint"] else "remove",
                "provider": provider,
                "providerType": "contract" if is_contract(w3, provider) else "wallet",
                "tokens": {
                    "token1": event['token1'],
                    "token2": event['token2'] if 'token2' in event else None
                },
                "token_amounts": {},
                "timestamp": event['timestamp'],
                "transactionHash": event['transactionHash']
            }

            if event_type in ["addliquidity", "removeliquidity", "removeliquidityimbalance"]:
                amounts = event['args'].get('token_amounts', [])
                formatted_event["token_amounts"]["token1"] = str(amounts[0]) if len(amounts) > 0 else '0'
                formatted_event["token_amounts"]["token2"] = str(amounts[1]) if len(amounts) > 1 else '0'
            elif event_type == "removeliquidityone":
                formatted_event["token_amounts"]["token1"] = str(event['args'].get('token_amount', 0))
                formatted_event["token_amounts"]["token2"] = '0'
            elif event_type in ["mint", "burn"]:
                # For UniswapV3, we need to match the token order with the pool's token order
                formatted_event["token_amounts"]["token1"] = str(event['args'].get('amount0', 0))
                formatted_event["token_amounts"]["token2"] = str(event['args'].get('amount1', 0))

            formatted_events.append(formatted_event)

        events_json = {"events": formatted_events}
        
        # Format rewards
        formatted_rewards = []
        for reward in rewards:
            provider = normalize_address(reward['provider'])
            
            formatted_rewards.append({
                "provider": provider,
                "weighted_avg_liquidity": str(reward['weighted_avg_liquidity']),
                "estimated_reward": str(reward['estimated_reward'])
            })
        
        rewards_json = {
            "overall_weighted_avg_liquidity": str(sum(float(r["weighted_avg_liquidity"]) for r in formatted_rewards)),
            "rewards": formatted_rewards
        }

        # Pin JSON data to IPFS
        events_response = pinata.pin_json_to_ipfs(events_json)
        rewards_response = pinata.pin_json_to_ipfs(rewards_json)
        
        # Debug logging
        logger.debug(f"Events response from Pinata: {events_response}")
        logger.debug(f"Rewards response from Pinata: {rewards_response}")

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
    
# API endpoint to get latest CIDs
@app.route('/api/latest-cids', methods=['GET'])
def get_latest_cids():
    state = load_state()
    logger.info(f"API request for latest CIDs. Returning: {state['events_cid']}, {state['rewards_cid']}")
    return jsonify({
        'events_cid': state['events_cid'],
        'rewards_cid': state['rewards_cid']
    }), 200

# Graceful shutdown
def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    while datetime.now() <= END_DATE + timedelta(days=1):
        try:
            asyncio.run(update_price_data())
            current_block = w3.eth.get_block('latest')['number']
            logger.info(f"Processing blocks from {START_BLOCK} to {current_block}")
            
            all_events = []
            for pool in POOLS:
                events = fetch_events(w3, pool, START_BLOCK, current_block, START_TIMESTAMP, END_TIMESTAMP)
                for event in events:
                    event['token1'] = pool['tokens'][0]
                    event['token2'] = pool['tokens'][1] if len(pool['tokens']) > 1 else None
                all_events.extend(events)

            logger.info(f"Total events fetched: {len(all_events)}")

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
        
        time.sleep(10800)  # Wait for 3 hours before the next iteration

if __name__ == "__main__":
    # Run the main loop in a separate thread
    import threading
    threading.Thread(target=main, daemon=True).start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)