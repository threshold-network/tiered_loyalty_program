import logging
from decimal import Decimal
import aiohttp
from src.config import PINATA_API_KEY, PINATA_SECRET_API_KEY
from src.utils.helpers import normalize_address, format_decimal, load_events

logger = logging.getLogger(__name__)

async def log_to_ipfs(rewards):
    try:
        events = load_events()
        logger.info(f"Logging {len(events)} events to IPFS")
        
        formatted_events = []

        for event in events:
            event_type = event['event']
            action = event['action']
            provider = event['args'].get('provider') or event['args'].get('owner')
            transactionHash = event['transactionHash']
            pool_address = event['pool_address']
            timestamp = event['timestamp']
            tokens = event['tokens']
            token0 = tokens.get('token0', {})
            token1 = tokens.get('token1', {})
            amounts = event['amounts']
            amount0 = amounts[0]
            amount1 = amounts[1]

            try:
                provider = normalize_address(provider)
            except Exception as e:
                logger.error(f"Error normalizing address: {str(e)}", exc_info=True)
                continue

            formatted_event = {
                "event": event_type,
                "action": action,
                "pool_address": pool_address,
                "provider": provider,
                "timestamp": timestamp,
                "transactionHash": transactionHash,
                "token0": {
                    "symbol": token0.get('symbol', ''),
                    "amount": format_decimal(amount0),
                    "decimals": token0.get('decimals', 0)
                },
                "token1": {
                    "symbol": token1.get('symbol', ''),
                    "amount": format_decimal(amount1),
                    "decimals": token1.get('decimals', 0)
                }
            }

            formatted_events.append(formatted_event)
      
        formatted_rewards = []

        for reward in rewards:
            provider = normalize_address(reward['provider'])
            
            formatted_rewards.append({
                "provider": provider,
                "weighted_avg_liquidity": format_decimal(reward['weighted_avg_liquidity']),
                "estimated_reward_in_arb_tokens": format_decimal(reward['estimated_reward_in_arb_tokens']),
                "estimated_reward_in_arb_usd": format_decimal(reward['estimated_reward_in_arb_usd']),
                "estimated_reward_in_t_usd": format_decimal(reward['estimated_reward_in_t_usd']),
                "estimated_reward_in_t_tokens": format_decimal(reward['estimated_reward_in_t_tokens'])
            })
        
        ipfs_json = {
            "overall_weighted_avg_liquidity": format_decimal(sum(Decimal(str(r["weighted_avg_liquidity"])) for r in rewards)),
            "rewards": formatted_rewards,
            "events": formatted_events
        }

        ipfs_json_cid = await pin_to_ipfs(ipfs_json)

        logger.info(f"New events pinned to IPFS with CID: {ipfs_json_cid}")
        
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