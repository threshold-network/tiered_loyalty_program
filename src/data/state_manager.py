import json
import logging
from src.config import STATE_FILE

logger = logging.getLogger(__name__)

def save_state(last_block, ipfs_json_cid):
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'last_processed_block': last_block,
            'ipfs_json_cid': ipfs_json_cid,
        }, f)

def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        return state
    except FileNotFoundError:
        logger.info(f"No state file found.")
        return {'last_processed_block': None, 'events_cid': None, 'rewards_cid': None}