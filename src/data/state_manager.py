import json
import logging
from src.config import STATE_FILE

logger = logging.getLogger(__name__)

def save_state(last_block, latest_rewards_file, last_balance_timestamp=None):
    state = {
        'last_processed_block': last_block,
        'latest_rewards_file': latest_rewards_file,
        'last_balance_timestamp': last_balance_timestamp
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        return state
    except FileNotFoundError:
        logger.info(f"No state file found.")
        return {'last_processed_block': None, 'latest_rewards_file': None, 'last_balance_timestamp': None}