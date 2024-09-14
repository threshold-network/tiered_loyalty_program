from web3 import Web3
import time
import logging
from src.config import INFURA_URL, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)

class Web3Client:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(INFURA_URL))

    def connect(self):
        for attempt in range(MAX_RETRIES):
            if self.w3.isConnected():
                logger.info("Successfully connected to Arbitrum network")
                return True
            else:
                logger.warning(f"Failed to connect to Arbitrum network. Attempt {attempt + 1} of {MAX_RETRIES}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
        
        logger.error(f"Failed to connect to Arbitrum network after {MAX_RETRIES} attempts")
        return False

    def get_latest_block(self):
        return self.w3.eth.get_block('latest')['number']

    def is_contract(self, address):
        code = self.w3.eth.get_code(address)
        return len(code) > 0

web3_client = Web3Client()