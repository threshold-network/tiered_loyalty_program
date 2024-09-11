import aiohttp
import logging
import asyncio
from datetime import datetime, timedelta
from src.config import COINGECKO_API_KEY, TOKENS, HISTORICAL_PRICES_FILE
from src.utils.helpers import load_price_data, save_price_data

logger = logging.getLogger(__name__)

async def coingecko_fetch(token_id, start_timestamp, end_timestamp):
    api_configs = [
        ("https://api.coingecko.com/api/v3", "x_cg_demo_api_key"),
        ("https://pro-api.coingecko.com/api/v3", "x_cg_pro_api_key")
    ]
    
    for base_url, api_key_param in api_configs:
        endpoint = f"{base_url}/coins/{token_id}/market_chart/range"
        params = {
            "vs_currency": "usd",
            "from": start_timestamp,
            "to": end_timestamp,
            api_key_param: COINGECKO_API_KEY,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["prices"]
                    else:
                        logger.warning(f"Error fetching data for {token_id} from {base_url}: {response.status}")
                        logger.warning(f"Response: {await response.text()}")
        except Exception as e:
            logger.warning(f"Exception occurred while fetching data for {token_id} from {base_url}: {str(e)}")
    
    logger.error(f"Failed to fetch data for {token_id} after all attempts")
    return None

async def update_price_data():
    historical_data = load_price_data(HISTORICAL_PRICES_FILE)
    end_timestamp = int(datetime.now().timestamp())

    tasks = []
    token_start_times = {}

    for token_name, token_id in TOKENS.items():
        if token_name in historical_data and historical_data[token_name]:
            last_timestamp = max(int(data[0]/1000) for data in historical_data[token_name])
            start_timestamp = last_timestamp + 1
        else:
            start_timestamp = int((datetime.now() - timedelta(days=730)).timestamp())

        if start_timestamp < end_timestamp:
            logger.info(f"Preparing to fetch new data for {token_name} from {datetime.fromtimestamp(start_timestamp)} to {datetime.fromtimestamp(end_timestamp)}")
            tasks.append(coingecko_fetch(token_id, start_timestamp, end_timestamp))
            token_start_times[token_name] = start_timestamp
        else:
            logger.info(f"Data for {token_name} is already up to date")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for token_name, result in zip(token_start_times.keys(), results):
        if isinstance(result, Exception):
            logger.error(f"An error occurred while updating {token_name}: {str(result)}")
        elif result:
            if token_name in historical_data:
                historical_data[token_name].extend(result)
                historical_data[token_name] = sorted(list({tuple(item) for item in historical_data[token_name]}))
            else:
                historical_data[token_name] = result
            
            logger.info(f"Updated data for {token_name}")
        else:
            logger.info(f"No new data available for {token_name}")

    save_price_data(historical_data, HISTORICAL_PRICES_FILE)
