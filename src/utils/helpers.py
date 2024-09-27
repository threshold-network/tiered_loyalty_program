from eth_utils import to_checksum_address
import json
from decimal import Decimal
import logging
from eth_abi import decode_abi
import bisect
import os

logger = logging.getLogger(__name__)

def normalize_address(address):
    """
    Normalize an Ethereum address to its checksummed version.
    This function handles both string and bytes input formats.

    :param address: Ethereum address to normalize.
    :return: Checksummed Ethereum address.
    """    
    if isinstance(address, bytes):
        address = address.hex()
    elif not isinstance(address, str):
        raise ValueError(f"Unsupported address format: {type(address)} for address {address}")

    address = address.lower().removeprefix('0x').lstrip('0').zfill(40)
    address = '0x' + address
    
    return to_checksum_address(address)

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

def get_ordered_token_amounts(event):
    event_type = event['event']
    if event_type in ["AddLiquidity", "RemoveLiquidity", "RemoveLiquidityImbalance"]:
        amounts = list(event['args'].get('token_amounts', []))
        return amounts + [0] * (2 - len(amounts))
    elif event_type in ["Mint", "Burn"]:
        return [event['args'].get('amount0', 0), event['args'].get('amount1', 0)]
    elif event_type == "RemoveLiquidityOne":
        token_id = event['args'].get('token_id', 0)
        coin_amount = event['args'].get('coin_amount', 0)
        if token_id == 0:
            return [coin_amount, 0]
        else:
            return [0, coin_amount]
    else:
        logger.warning(f"Unknown event type: {event_type}")
        return [0, 0]
    
def format_decimal(value, decimal_places=8):
    """
    Format a decimal value with a specified number of decimal places by truncating.
    
    :param value: The value to format.
    :param decimal_places: The number of decimal places to keep after truncating.
    :return: Formatted string representation of the value.
    """
    full_string = format(Decimal(str(value)), 'f')
    
    parts = full_string.split('.')
    
    if len(parts) > 1:
        return f"{parts[0]}.{parts[1][:decimal_places]}"
    else:
        return parts[0]

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

def get_tokens_from_contract(w3, pool):
    contract = w3.eth.contract(address=pool["address"], abi=pool["abi"])
    try:
        if hasattr(contract.functions, 'token0') and hasattr(contract.functions, 'token1'):
            token0_address = contract.functions.token0().call()
            token1_address = contract.functions.token1().call()
        elif hasattr(contract.functions, 'coins'):
            token0_address = contract.functions.coins(0).call()
            token1_address = contract.functions.coins(1).call()
        else:
            logger.error(f"Unable to determine token addresses for pool {pool['address']}")
            return None, None

        token0_attr = get_token_attr_by_address(token0_address, pool)
        token1_attr = get_token_attr_by_address(token1_address, pool)

        if token0_attr and token1_attr:
            return token0_attr, token1_attr
        else:
            logger.error(f"Unable to find token attributes for addresses {token0_address} and {token1_address}")
            return None, None
    except Exception as e:
        logger.error(f"Error fetching token addresses from contract: {str(e)}")
        return None, None

def get_token_attr_by_address(address, pool):
    for token in pool['tokens']:
        token_info = next(iter(token.values()))
        if token_info['address'].lower() == address.lower():
            return token_info
    return None

def get_token_price(coingecko_id, date, path):
    historical_data = load_price_data(path)
    if not coingecko_id or coingecko_id not in historical_data:
        logger.error(f"Unknown token or no price data: {coingecko_id}")
        return 0

    target_timestamp = int(date.timestamp() * 1000)  # Convert to milliseconds
    price_data = historical_data[coingecko_id]
    
    timestamps = [entry[0] for entry in price_data]
    index = bisect.bisect_left(timestamps, target_timestamp)
    
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

def load_price_data(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Historical prices file not found: {path}")
        return {}

def save_price_data(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_events():
    file_path = os.path.join('data', 'pools_events.json')
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"No events file found at {file_path}")
        return []

def convert_to_serializable(obj):
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(v) for v in obj]
    elif hasattr(obj, 'hex'):
        return obj.hex()
    else:
        return obj

def sort_events(event):
    return (
        event.get('provider'),
        event.get('timestamp'), 
        0 if event.get('action') == 'add' else 1
    )

