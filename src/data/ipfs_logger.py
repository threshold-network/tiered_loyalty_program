import logging
import aiohttp
from src.config import PINATA_API_KEY, PINATA_SECRET_API_KEY
from src.data.json_formatter import format_rewards_data

logger = logging.getLogger(__name__)

async def log_to_ipfs(rewards_data):
    try:
        formatted_data = format_rewards_data(rewards_data)
        ipfs_json_cid = await pin_to_ipfs(formatted_data)
        logger.info(f"Data pinned to IPFS with CID: {ipfs_json_cid}")
        return ipfs_json_cid
    except Exception as e:
        logger.error(f"Error logging to IPFS: {str(e)}", exc_info=True)
        raise

async def pin_to_ipfs(data):
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        'Content-Type': 'application/json',
        'pinata_api_key': PINATA_API_KEY,
        'pinata_secret_api_key': PINATA_SECRET_API_KEY
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json['IpfsHash']
            else:
                raise Exception(f"Failed to pin to IPFS: {await response.text()}")