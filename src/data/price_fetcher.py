import aiohttp
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from src.config import COINGECKO_API_KEY, TOKENS, HISTORICAL_PRICES_FILE, START_TIMESTAMP
from src.utils.helpers import load_price_data, save_price_data

logger = logging.getLogger(__name__)

async def coingecko_fetch(token_id, start_timestamp, end_timestamp):
    # Use only the Public API, but include demo key if available
    endpoint_public = f"https://api.coingecko.com/api/v3/coins/{token_id}/market_chart/range"
    params_public = {
            "vs_currency": "usd",
            "from": start_timestamp,
            "to": end_timestamp,
        # Remove interval, let CoinGecko decide based on range
        # "interval": "daily", 
    }
    
    # Add the demo API key to parameters if it's set
    if COINGECKO_API_KEY:
        params_public["x_cg_demo_api_key"] = COINGECKO_API_KEY
        logger.debug("Using CoinGecko Demo API Key")
    else:
        logger.debug("No CoinGecko API Key found, using anonymous public access")

    try:
        async with aiohttp.ClientSession() as session:
            logger.debug(f"Attempting Public API fetch for {token_id}")
            async with session.get(endpoint_public, params=params_public) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched data for {token_id} from Public API")
                    return data.get("prices") # Use .get for safety
                elif response.status == 429: # Handle rate limiting specifically
                    logger.warning(f"Rate limited fetching data for {token_id} from Public API: {response.status}. Retrying may be necessary.")
                    # Consider adding retry logic here if needed
                else:
                    logger.warning(f"Error fetching data for {token_id} from Public API: {response.status}")
                    logger.warning(f"Response: {await response.text()}")
    except Exception as e:
        logger.warning(f"Exception occurred while fetching data for {token_id} from Public API: {str(e)}")
    
    logger.error(f"Failed to fetch data for {token_id} after all attempts")
    return None

async def update_price_data():
    historical_data = load_price_data(HISTORICAL_PRICES_FILE)
    end_timestamp = int(datetime.now(timezone.utc).timestamp())

    tasks = []
    token_start_times = {}

    for token_name, token_id in TOKENS.items():
        if token_id in historical_data and historical_data[token_id]:
            # Token data exists, find the last timestamp and start from the next second
            last_timestamp = max(int(data[0]/1000) for data in historical_data[token_id])
            start_timestamp = last_timestamp + 1 
            logger.info(f"Found existing data for {token_name}. Fetching from {datetime.fromtimestamp(start_timestamp, tz=timezone.utc)}")
        else:
            # No data for this token, start from the program's START_DATE
            start_timestamp = START_TIMESTAMP
            logger.info(f"No existing data for {token_name}. Fetching from program START_DATE: {datetime.fromtimestamp(start_timestamp, tz=timezone.utc)}")

        # Ensure start_timestamp doesn't exceed end_timestamp (e.g., if START_DATE is in the future)
        start_timestamp = min(start_timestamp, end_timestamp)

        if start_timestamp < end_timestamp:
            logger.info(f"Preparing price fetch task for {token_name} ({token_id}) from {datetime.fromtimestamp(start_timestamp, tz=timezone.utc)} to {datetime.fromtimestamp(end_timestamp, tz=timezone.utc)}")
            tasks.append(coingecko_fetch(token_id, start_timestamp, end_timestamp))
            token_start_times[token_id] = start_timestamp
        else:
            logger.info(f"Price data for {token_name} ({token_id}) is already up to date (start_timestamp >= end_timestamp).")

    if not tasks:
        logger.info("No price updates needed for any tokens.")
        return
        
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for token_id, result in zip(token_start_times.keys(), results):
        token_name = next((name for name, tid in TOKENS.items() if tid == token_id), "Unknown")
        if isinstance(result, Exception):
            logger.error(f"An error occurred while fetching prices for {token_name} ({token_id}): {str(result)}")
        elif result:
            if token_id not in historical_data:
                historical_data[token_id] = []
            
            # Add new prices and remove duplicates based on timestamp
            existing_timestamps = {data[0] for data in historical_data[token_id]}
            new_prices_added = 0
            for price_entry in result:
                if price_entry[0] not in existing_timestamps:
                    historical_data[token_id].append(price_entry)
                    existing_timestamps.add(price_entry[0])
                    new_prices_added += 1
            
            # Sort by timestamp after adding new entries
            historical_data[token_id].sort(key=lambda x: x[0])
            
            logger.info(f"Added {new_prices_added} new price entries for {token_name} ({token_id}). Total entries: {len(historical_data[token_id])}")
        else:
            logger.info(f"No new price data returned for {token_name} ({token_id}) from fetch operation.")

    save_price_data(historical_data, HISTORICAL_PRICES_FILE)