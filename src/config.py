import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from eth_utils import to_checksum_address
from src.utils.helpers import load_abi
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Environment variables
ALCHEMY_URL = os.getenv("ALCHEMY_URL") # Prioritize Alchemy URL
INFURA_KEY = os.getenv("INFURA_KEY") # Keep as fallback if needed
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")
TOTAL_REWARDS = float(os.getenv("TOTAL_REWARDS", 0)) # Add default
START_DATE_STR = os.getenv("START_DATE", "")
PROGRAM_DURATION_WEEKS_STR = os.getenv("PROGRAM_DURATION_WEEKS", "0")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# --- Input Validation and Defaults ---

# Validate and parse START_DATE
try:
    START_DATE = datetime.fromisoformat(START_DATE_STR).replace(tzinfo=timezone.utc)
except ValueError:
    logger.error(f"Invalid START_DATE format: '{START_DATE_STR}'. Please use ISO format (YYYY-MM-DDTHH:MM:SS). Using current time as fallback.")
    START_DATE = datetime.now(timezone.utc)

# Validate and parse PROGRAM_DURATION_WEEKS
try:
    PROGRAM_DURATION_WEEKS = int(PROGRAM_DURATION_WEEKS_STR)
    if PROGRAM_DURATION_WEEKS <= 0:
        logger.warning("PROGRAM_DURATION_WEEKS must be positive. Setting to 1 week as fallback.")
        PROGRAM_DURATION_WEEKS = 1
except ValueError:
    logger.error(f"Invalid PROGRAM_DURATION_WEEKS: '{PROGRAM_DURATION_WEEKS_STR}'. Must be an integer. Setting to 1 week as fallback.")
    PROGRAM_DURATION_WEEKS = 1

# --- Derived constants ---
END_DATE = START_DATE + timedelta(weeks=PROGRAM_DURATION_WEEKS)
START_TIMESTAMP = int(START_DATE.timestamp())
END_TIMESTAMP = int(END_DATE.timestamp())

# --- Web3 configuration ---
# Determine RPC URL based on available keys, prioritizing Alchemy
if ALCHEMY_URL:
    RPC_URL = ALCHEMY_URL
    logger.info("Using Alchemy RPC URL")
elif INFURA_KEY:
    RPC_URL = f"https://arbitrum-mainnet.infura.io/v3/{INFURA_KEY}"
    logger.warning("ALCHEMY_URL not set, falling back to Infura RPC URL")
else:
    logger.error("Neither ALCHEMY_URL nor INFURA_KEY environment variables are set. Web3 connection will fail.")
    RPC_URL = "" # Set to empty string or handle error appropriately

MAX_RETRIES = 5
RETRY_DELAY = 10
# PROCESS_BLOCK_RANGE_SIZE = 1_000_000 # Keep this commented out as user rejected it

# --- ABIs ---
CURVE_ABI = load_abi("curve_abi.json")
UNIV3_ABI = load_abi("univ3_abi.json")

# --- File paths ---
STATE_FILE = 'data/program_state.json'
HISTORICAL_PRICES_FILE = 'data/token_historical_prices.json'

# --- Pool configurations ---
POOLS = [
    {
        "address": to_checksum_address("0x186cf879186986a20aadfb7ead50e3c20cb26cec"),
        "abi": CURVE_ABI,
        "deploy_date": datetime.fromisoformat("2024-06-19"),
        #"deploy_block": 254700000, #test purposes comment this for PRODUCTION
        "deploy_block": 223607824, #set the block number -1
        "tokens": [
            {"token0": {"address": "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40", "decimals": 18, "symbol": "tBTC", "coingecko_id": "tbtc"}},
            {"token1": {"address": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", "decimals": 8, "symbol": "WBTC", "coingecko_id": "wrapped-bitcoin"}}
        ],
        "events": ["AddLiquidity", "RemoveLiquidity", "RemoveLiquidityOne", "RemoveLiquidityImbalance"]
    },
    {
        "address": to_checksum_address("0xe9e6b9aaafaf6816c3364345f6ef745ccfc8660a"),
        "abi": UNIV3_ABI,
        "deploy_date": datetime.fromisoformat("2023-05-16"),
        #"deploy_block": 254700000, #test purposes comment this for PRODUCTION
        "deploy_block": 91124443, #set the block number -1
        "tokens": [
            {"token0": {"address": "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40", "decimals": 18, "symbol": "tBTC", "coingecko_id": "tbtc"}},
            {"token1": {"address": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", "decimals": 8, "symbol": "WBTC", "coingecko_id": "wrapped-bitcoin"}}
        ],
        "events": ["Burn", "Mint"]
    },
    {
        "address": to_checksum_address("0xCb198a55e2a88841E855bE4EAcaad99422416b33"),
        "abi": UNIV3_ABI,
        "deploy_date": datetime.fromisoformat("2023-05-16"),
        #"deploy_block": 254700000, #test purposes comment this for PRODUCTION
        "deploy_block": 91123769, #set the block number -1
        "tokens": [
            {"token0": {"address": "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40", "decimals": 18, "symbol": "tBTC", "coingecko_id": "tbtc"}},
            {"token1": {"address": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "decimals": 18, "symbol": "ETH", "coingecko_id": "ethereum"}}
        ],
        "events": ["Burn", "Mint"]
    }
]

# --- Tokens for Price Fetching ---
TOKENS = {
    "tBTC": "tbtc",
    "WBTC": "wrapped-bitcoin",
    "ETH": "ethereum",
    "ARB": "arbitrum",
    "T": "threshold-network-token",
}
