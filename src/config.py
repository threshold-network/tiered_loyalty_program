import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from eth_utils import to_checksum_address
from src.utils.helpers import load_abi

load_dotenv()

# Environment variables
INFURA_KEY = os.getenv("INFURA_KEY")
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")
TOTAL_REWARDS = float(os.getenv("TOTAL_REWARDS"))
START_DATE = datetime.fromisoformat(os.getenv("START_DATE")).replace(tzinfo=timezone.utc)
PROGRAM_DURATION_WEEKS = int(os.getenv("PROGRAM_DURATION_WEEKS"))
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Derived constants
END_DATE = START_DATE + timedelta(weeks=PROGRAM_DURATION_WEEKS)
START_TIMESTAMP = int(START_DATE.timestamp())
END_TIMESTAMP = int(END_DATE.timestamp())

#ABIs
CURVE_ABI = load_abi("curve_abi.json")
UNIV3_ABI = load_abi("univ3_abi.json")

# File paths
STATE_FILE = 'data/program_state.json'
HISTORICAL_PRICES_FILE = 'data/token_historical_prices.json'

# Web3 configuration
INFURA_URL = f"https://arbitrum-mainnet.infura.io/v3/{INFURA_KEY}"
MAX_RETRIES = 5
RETRY_DELAY = 10

# Pool configurations
POOLS = [
    {
        "address": to_checksum_address("0x186cf879186986a20aadfb7ead50e3c20cb26cec"),
        "abi": CURVE_ABI,
        "deploy_date": datetime.fromisoformat("2024-06-19"),
        "deploy_block": 251533086, #specify the block number -1
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
        "deploy_block": 251533086, #specify the block number -1
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
        "deploy_block": 251533086, #specify the block number -1
        "tokens": [
            {"token0": {"address": "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40", "decimals": 18, "symbol": "tBTC", "coingecko_id": "tbtc"}},
            {"token1": {"address": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "decimals": 18, "symbol": "ETH", "coingecko_id": "ethereum"}}
        ],
        "events": ["Burn", "Mint"]
    }
]
# Token configurations
TOKENS = {
    "tbtc": "tbtc",
    "wrapped-bitcoin": "wrapped-bitcoin",
    "ethereum": "ethereum",
    "arbitrum": "arbitrum",
    "threshold-network-token": "threshold-network-token",
}
