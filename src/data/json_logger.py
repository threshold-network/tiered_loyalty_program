import os
import json
import logging
from datetime import datetime
from src.data.json_formatter import format_rewards_data

logger = logging.getLogger(__name__)

def save_json_data(data, filename_prefix='data'):
    formatted_rewards = format_rewards_data(data)
    rewards_dir = os.path.join(os.getcwd(), 'data', 'rewards')
    os.makedirs(rewards_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rewards_file = os.path.join('data', 'rewards', f'{filename_prefix}_{timestamp}.json')
    full_path = os.path.join(os.getcwd(), rewards_file)
    
    with open(full_path, 'w') as f:
        json.dump(formatted_rewards, f, indent=2)
    
    logger.info(f"Data saved to {full_path}")
    return rewards_file