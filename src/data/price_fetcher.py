import aiohttp
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from src.config import COINGECKO_API_KEY, TOKENS, HISTORICAL_PRICES_FILE
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
            last_timestamp = max(int(data[0]/1000) for data in historical_data[token_id])
            start_timestamp = last_timestamp + 1
        else:
            start_timestamp = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())

        if start_timestamp < end_timestamp:
            logger.info(f"Preparing to fetch new data for {token_name} from {datetime.fromtimestamp(start_timestamp)} to {datetime.fromtimestamp(end_timestamp)}")
            tasks.append(coingecko_fetch(token_id, start_timestamp, end_timestamp))
            token_start_times[token_id] = start_timestamp
        else:
            logger.info(f"Data for {token_name} is already up to date")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for token_id, result in zip(token_start_times.keys(), results):
        if isinstance(result, Exception):
            logger.error(f"An error occurred while updating {token_name}: {str(result)}")
        elif result:
            if token_id in historical_data:
                historical_data[token_id].extend(result)
                historical_data[token_id] = sorted(list({tuple(item) for item in historical_data[token_id]}))
            else:
                historical_data[token_id] = result
            
            logger.info(f"Updated data for {token_id}")
        else:
            logger.info(f"No new data available for {token_id}")

    save_price_data(historical_data, HISTORICAL_PRICES_FILE)
