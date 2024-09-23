import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, send_file
import signal
import sys
from flask_cors import CORS
import asyncio
import os
import traceback

from src.config import END_DATE, POOLS
from src.blockchain.web3_client import web3_client
from src.blockchain.event_fetcher import event_fetcher
from src.data.price_fetcher import update_price_data
from src.rewards.calculator import calculate_rewards
from src.data.state_manager import save_state, load_state
from src.data.json_logger import save_json_data
from src.rewards.balance_calculator import balance_calculator

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

    @app.route('/api/get_latest_rewards', methods=['GET'])
    def get_latest_rewards():
        state = load_state()
        latest_rewards_file = state.get('latest_rewards_file')
        if latest_rewards_file:
            # Ensure the path starts from the project root
            full_path = os.path.join(os.getcwd(), latest_rewards_file)
            if os.path.exists(full_path):
                return send_file(full_path, mimetype='application/json')
            else:
                logger.warning(f"Rewards file not found: {full_path}")
        else:
            logger.warning("No latest rewards file found in state")
        return jsonify({"error": "No rewards data available"}), 404

    logger.info("Application created")
    return app

def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    logger.info("Starting main async loop")
    while datetime.now(timezone.utc) <= END_DATE + timedelta(days=1):
        try:
            # await update_price_data()
            # current_block = web3_client.get_latest_block()
            
            # state = load_state()
            # logger.info(f"State loaded. Last processed block: {state['last_processed_block']}")
            # last_processed_block = state.get('last_processed_block')
            
            # if last_processed_block is None:
            #     last_processed_block = min(pool['deploy_block'] for pool in POOLS)

            # if last_processed_block + 1 <= current_block:
            #     await event_fetcher.fetch_and_save_events(POOLS, last_processed_block + 1, current_block)
            # else:
            #     logger.info("No new blocks to process.")
            
            balance_calculator.calculate_balances()
            
            # rewards_data = await calculate_rewards()
            # rewards_file = save_json_data(rewards_data, filename_prefix='rewards')
            
            # save_state(current_block, rewards_file, balance_calculator.last_processed_timestamp)
            # logger.info(f"State saved. Last processed block: {current_block}, Last balance timestamp: {balance_calculator.last_processed_timestamp}")
        except Exception as e:
            logger.error(f"An error occurred in the main loop: {str(e)}")
            logger.error(traceback.format_exc())
            await asyncio.sleep(10800)
        
        logger.info(f"Sleeping for 12 hours")
        await asyncio.sleep(43200)

if __name__ == "__main__":
    app = create_app()
    asyncio.run(main())
