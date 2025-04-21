from web3 import Web3
from web3.exceptions import ContractLogicError
import time
import logging
import requests # Import requests to check for HTTP errors
from src.config import RPC_URL, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)

class Web3Client:
    def __init__(self):
        if not RPC_URL:
            logger.critical("RPC_URL is not configured. Please set ALCHEMY_URL or INFURA_KEY environment variable.")
            # Handle this case more gracefully, maybe raise an exception or exit
            # For now, initializing with empty URL which will likely fail on connect()
            self.w3 = Web3(Web3.HTTPProvider("")) 
        else:
             self.w3 = Web3(Web3.HTTPProvider(RPC_URL))

    def connect(self):
        if not RPC_URL:
             logger.error("Cannot connect: RPC_URL is not configured.")
             return False
             
        for attempt in range(MAX_RETRIES):
            try:
                if self.w3.is_connected(): # Use is_connected() instead of deprecated isConnected()
                    logger.info("Successfully connected to Arbitrum network via RPC")
                    return True
            except Exception as e:
                 logger.warning(f"Connection check failed: {e}")
            
            logger.warning(f"Failed to connect to Arbitrum network. Attempt {attempt + 1} of {MAX_RETRIES}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
        
        logger.error(f"Failed to connect to Arbitrum network after {MAX_RETRIES} attempts")
        return False

    def get_latest_block(self):
        # Wrap this call as well, though less likely to be rate-limited
        return self.call_with_retry(self.w3.eth.get_block, 'latest')['number']

    def is_contract(self, address):
        code = self.call_with_retry(self.w3.eth.get_code, address)
        return code is not None and len(code) > 0

    def call_with_retry(self, func, *args, **kwargs):
        retries = kwargs.pop('max_retries', MAX_RETRIES)
        delay = kwargs.pop('retry_delay', RETRY_DELAY)
        backoff_factor = kwargs.pop('backoff_factor', 2) # Exponential backoff factor
        
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429: # Too Many Requests
                    logger.warning(f"Rate limit exceeded (429). Attempt {attempt + 1}/{retries}. Retrying in {delay}s...")
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay *= backoff_factor # Increase delay for next retry
                    else:
                        logger.error(f"Max retries ({retries}) reached for rate-limited request.")
                        raise # Re-raise the exception after max retries
                else:
                    # Handle other HTTP errors if necessary, or just re-raise
                    logger.error(f"HTTPError encountered: {e}")
                    raise
            except ContractLogicError as e:
                 # Handle contract specific errors (e.g., reverts) if needed
                 logger.error(f"ContractLogicError: {e}")
                 raise # Or return a specific value/indicator
            except Exception as e:
                # Catch other potential exceptions during the call
                logger.error(f"An unexpected error occurred during web3 call: {e}")
                # Decide whether to retry or raise immediately based on the error type
                # For now, re-raising for unexpected errors
                raise
        # This point should ideally not be reached if exceptions are handled/raised properly
        logger.error("Exited retry loop unexpectedly.")
        return None # Or raise an error


web3_client = Web3Client()