import os
import json
import time
import logging
from datetime import datetime, timedelta
from web3 import Web3
from eth_abi import decode_abi
from dotenv import load_dotenv
import requests
from flask import Flask, jsonify
import pinatapy
import signal
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    {"address": to_checksum_address("0x186cf879186986a20aadfb7ead50e3c20cb26cec"), "abi": CURVE_ABI, "tokens": ["tbtc", "wbtc"], "event": "AddLiquidity"},
    {"address": to_checksum_address("0xe9e6b9aaafaf6816c3364345f6ef745ccfc8660a"), "abi": UNIV3_ABI, "tokens": ["tbtc", "wbtc"], "event": "Mint"},
    {"address": to_checksum_address("0xCb198a55e2a88841E855bE4EAcaad99422416b33"), "abi": UNIV3_ABI, "tokens": ["tbtc", "eth"], "event": "Mint"}
]

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

def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'last_processed_block': START_BLOCK, 'events_cid': None, 'rewards_cid': None}

# Rate limiting for CoinGecko API
last_request_time = {}
def rate_limited_request(url, params):
    current_time = time.time()
    if url in last_request_time and current_time - last_request_time[url] < 1:
        time.sleep(1 - (current_time - last_request_time[url]))
    response = requests.get(url, params=params)
    last_request_time[url] = time.time()
    return response

# Function to fetch token price from CoinGecko at a specific date
def fetch_token_price(token_name, date):
    token_id = TOKEN_TO_COINGECKO_ID.get(token_name.lower())
    if not token_id:
        logger.error(f"Unknown token: {token_name}")
        return 0

    url = f"https://api.coingecko.com/api/v3/coins/{token_id}/history"
    
    for i in range(4):  # Try current date and up to 3 days before
        try_date = date - timedelta(days=i)
        params = {
            "date": try_date.strftime("%d-%m-%Y"),
            "localization": "false"
        }
        try:
            response = rate_limited_request(url, params)
            response.raise_for_status()
            data = response.json()
            price = data['market_data']['current_price']['usd']
            if price > 0:
                if i > 0:
                    logger.info(f"Used price from {i} day(s) ago for {token_name} on {date}")
                return price
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch price for {token_name} on {try_date}: {str(e)}")
    
    logger.error(f"Failed to fetch price for {token_name} on {date} and 3 days prior")
    return 0

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
            
            for log in logs:
                try:
                    block = w3.eth.get_block(log['blockNumber'])
                    event_timestamp = block['timestamp']
                    if start_timestamp <= event_timestamp < end_timestamp:
                        decoded_event = decode_log(event_abi, log)
                        decoded_event['timestamp'] = event_timestamp
                        decoded_event['transactionHash'] = log['transactionHash'].hex()
                        all_events.append(decoded_event)
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to fetch events for pool {pool['address']}: {str(e)}")

    return all_events

# Function to calculate rewards based on events
def calculate_rewards(events):
    provider_liquidity = {}
    end_timestamp = datetime.now()

    sorted_events = sorted(events, key=lambda x: x['timestamp'])

    for event in sorted_events:
        provider = event['args']['provider'] if 'provider' in event['args'] else event['args']['owner']
        timestamp = datetime.fromtimestamp(event['timestamp'])
        event_type = event['event']
        
        try:
            if event_type in ["AddLiquidity", "Mint"]:
                action = "add"
                if event_type == "AddLiquidity":
                    amounts = event['args']['token_amounts']
                else:  # Mint event
                    amounts = [event['args']['amount0'], event['args']['amount1']]
            elif event_type in ["RemoveLiquidity", "RemoveLiquidityOne", "RemoveLiquidityImbalance", "Burn"]:
                action = "remove"
                if event_type in ["RemoveLiquidity", "RemoveLiquidityImbalance"]:
                    amounts = event['args']['token_amounts']
                elif event_type == "RemoveLiquidityOne":
                    amounts = [event['args']['token_amount'], 0]  # Assuming it's always the first token
                else:  # Burn event
                    amounts = [event['args']['amount0'], event['args']['amount1']]

            token1_price = fetch_token_price(event['token1'], timestamp)
            token2_price = fetch_token_price(event['token2'], timestamp)

            total_value = (amounts[0] * token1_price) + (amounts[1] * token2_price)

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
        except Exception as e:
            logger.error(f"Error calculating rewards for event: {str(e)}")

    weighted_avg_liquidity = {}
    for provider, liquidity_events in provider_liquidity.items():
        total_liquidity_time = 0
        for i in range(len(liquidity_events)):
            current_time, current_amount = liquidity_events[i]
            
            if i < len(liquidity_events) - 1:
                next_time = liquidity_events[i+1][0]
            else:
                next_time = end_timestamp

            duration = (next_time - current_time).total_seconds()
            total_liquidity_time += current_amount * duration

        total_duration = (end_timestamp - liquidity_events[0][0]).total_seconds()
        weighted_avg_liquidity[provider] = total_liquidity_time / total_duration

    total_weighted_liquidity = sum(weighted_avg_liquidity.values())
    rewards = []
    for provider, avg_liquidity in weighted_avg_liquidity.items():
        provider_reward = (avg_liquidity / total_weighted_liquidity) * TOTAL_REWARDS
        rewards.append({
            "provider": provider,
            "weighted_avg_liquidity": avg_liquidity,
            "estimated_reward": provider_reward
        })

    return rewards

# Function to log events and rewards to IPFS
def log_to_ipfs(new_events, rewards):
    state = load_state()
    events_cid = state['events_cid']
    
    try:
        if events_cid:
            response = requests.get(f'https://gateway.pinata.cloud/ipfs/{events_cid}')
            response.raise_for_status()
            existing_events = response.json()['events']
        else:
            existing_events = []

        all_events = existing_events + new_events
        unique_events = {event['transactionHash']: event for event in all_events}.values()

        events_json = json.dumps({"events": list(unique_events)})
        rewards_json = json.dumps({
            "overall_weighted_avg_liquidity": sum(r["weighted_avg_liquidity"] for r in rewards),
            "rewards": rewards
        })
        
        events_response = pinata.pin_json(events_json)
        rewards_response = pinata.pin_json(rewards_json)
        
        new_events_cid = events_response['IpfsHash']
        new_rewards_cid = rewards_response['IpfsHash']
        
        return new_events_cid, new_rewards_cid
    except Exception as e:
        logger.error(f"Error logging to IPFS: {str(e)}")
        raise

# API endpoint to get latest CIDs
@app.route('/api/latest-cids', methods=['GET'])
def get_latest_cids():
    state = load_state()
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
    state = load_state()
    last_processed_block = state['last_processed_block']
    
    while datetime.now() < END_DATE:
        try:
            current_block = w3.eth.get_block('latest')['number']
            
            all_events = []
            for pool in POOLS:
                events = fetch_events(w3, pool, last_processed_block, current_block, START_TIMESTAMP, END_TIMESTAMP)
                for event in events:
                    event['token1'] = pool['tokens'][0]
                    event['token2'] = pool['tokens'][1]
                all_events.extend(events)
            
            if all_events:
                rewards = calculate_rewards(all_events)
                events_cid, rewards_cid = log_to_ipfs(all_events, rewards)
                
                save_state(current_block, events_cid, rewards_cid)
                
                logger.info(f"Events logged to IPFS with CID: {events_cid}")
                logger.info(f"Rewards logged to IPFS with CID: {rewards_cid}")
            else:
                logger.info("No new events in the specified date range.")
            
            last_processed_block = current_block + 1
        except Exception as e:
            logger.error(f"An error occurred in the main loop: {str(e)}")
            time.sleep(60)  # Wait for 1 minute before retrying
        
        time.sleep(5)  # Wait for 5 secs before the next iteration

if __name__ == "__main__":
    # Run the main loop in a separate thread
    import threading
    threading.Thread(target=main, daemon=True).start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)