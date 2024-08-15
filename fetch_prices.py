import aiohttp
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import asyncio

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# CoinGecko API endpoint
base_url = "https://api.coingecko.com/api/v3"

# API key from environment variable
api_key = os.getenv("COINGECKO_API_KEY")

# Token IDs
tokens = {
    "tbtc": "tbtc",
    "wrapped-bitcoin": "wrapped-bitcoin",
    "ethereum": "ethereum",
    "arbitrum": "arbitrum",
    "threshold-network-token": "threshold-network-token",
}

# Output file name
output_file = "token_historical_prices.json"

async def fetch_historical_data(token_id, start_timestamp, end_timestamp):
    endpoint = f"{base_url}/coins/{token_id}/market_chart/range"
    params = {
        "vs_currency": "usd",
        "from": start_timestamp,
        "to": end_timestamp,
        "x_cg_demo_api_key": api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data["prices"]
            else:
                logger.error(f"Error fetching data for {token_id}: {response.status}")
                logger.error(f"Response: {await response.text()}")
                return None

def load_existing_data():
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

async def update_price_data():
    # Load existing data
    historical_data = load_existing_data()

    # Get current timestamp (in seconds)
    end_timestamp = int(datetime.now().timestamp())

    tasks = []
    token_start_times = {}

    # Prepare tasks for each token
    for token_name, token_id in tokens.items():
        if token_name in historical_data and historical_data[token_name]:
            last_timestamp = max(int(data[0]/1000) for data in historical_data[token_name])
            start_timestamp = last_timestamp + 1
        else:
            start_timestamp = int((datetime.now() - timedelta(days=365)).timestamp())

        if start_timestamp < end_timestamp:
            logger.info(f"Preparing to fetch new data for {token_name} from {datetime.fromtimestamp(start_timestamp)} to {datetime.fromtimestamp(end_timestamp)}")
            tasks.append(fetch_historical_data(token_id, start_timestamp, end_timestamp))
            token_start_times[token_name] = start_timestamp
        else:
            logger.info(f"Data for {token_name} is already up to date")

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for token_name, result in zip(token_start_times.keys(), results):
        if isinstance(result, Exception):
            logger.error(f"An error occurred while updating {token_name}: {str(result)}")
        elif result:
            if token_name in historical_data:
                historical_data[token_name].extend(result)
                # Remove duplicates and sort
                historical_data[token_name] = sorted(list({tuple(item) for item in historical_data[token_name]}))
            else:
                historical_data[token_name] = result
            
            logger.info(f"Updated data for {token_name}")
        else:
            logger.info(f"No new data available for {token_name}")

    # Save updated data
    save_data(historical_data)
    logger.info(f"Historical price data updated and saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(update_price_data())