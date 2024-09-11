import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from flask import Flask, jsonify
import signal
import sys
from flask_cors import CORS
import asyncio

from src.config import END_DATE, POOLS
from src.blockchain.web3_client import web3_client
from src.blockchain.event_fetcher import event_fetcher
from src.data.price_fetcher import update_price_data
from src.rewards.calculator import calculate_rewards
from src.data.ipfs_logger import log_to_ipfs
from src.data.state_manager import save_state, load_state

# Set up logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

def create_app():
    app = Flask(__name__)
    CORS(app)

    @app.route('/api/latest-cids', methods=['GET'])
    def get_latest_cids():
        state = load_state()
        logger.info(f"API request for latest CIDs. Returning: {state['events_cid']}, {state['rewards_cid']}")
        return jsonify({
            'events_cid': state['events_cid'],
            'rewards_cid': state['rewards_cid']
        }), 200

    logger.info("Application created")
    return app

def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    logger.info("Starting main async loop")
    while datetime.now() <= END_DATE + timedelta(days=1):
        try:
            await update_price_data()
            current_block = web3_client.get_latest_block()
            
            state = load_state()
            logger.info(f"State loaded. Last processed block: {state['last_processed_block']}")
            last_processed_block = state.get('last_processed_block')
            
            if last_processed_block is None:
                last_processed_block = min(pool['deploy_block'] for pool in POOLS)
            
            new_events = await event_fetcher.fetch_and_save_events(POOLS, last_processed_block, current_block)

            logger.info(f"Total new events: {len(new_events)}")
            
            if not new_events:
                logger.info("No new events in the specified date range.")

            rewards = await calculate_rewards()
            ipfs_json_cid = await log_to_ipfs(rewards)
            save_state(current_block, ipfs_json_cid)
            logger.info(f"State saved. Last processed block: {current_block}")
        except Exception as e:
            logger.error(f"An error occurred in the main loop: {str(e)}")
            await asyncio.sleep(10800)  # Wait for 3 hours before retrying
        
        logger.info(f"Sleeping for 24 hours")
        await asyncio.sleep(86400)

if __name__ == "__main__":
    app = create_app()
    asyncio.run(main())