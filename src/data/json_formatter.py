import logging
from src.utils.helpers import normalize_address, format_decimal

logger = logging.getLogger(__name__)

def format_rewards_data(rewards_data):
    try:
        total_weighted_liquidity = rewards_data['total_weighted_liquidity']
        rewards = rewards_data['rewards']
        events = rewards_data['events']
        
        formatted_events = []

        for event in events:
            formatted_event = {
                "event": event['event'],
                "action": event['action'],
                "pool_address": event['pool_address'],
                "provider": normalize_address(event['provider']),
                "timestamp": event['timestamp'],
                "transactionHash": event['transactionHash'],
                "token0": {
                    "symbol": event['token0']['symbol'],
                    "amount": format_decimal(event['token0']['amount']),
                    "decimals": event['token0']['decimals']
                },
                "token1": {
                    "symbol": event['token1']['symbol'],
                    "amount": format_decimal(event['token1']['amount']),
                    "decimals": event['token1']['decimals']
                },
                "balance_date": int(event['balance_date'].timestamp()),
                "event_balance": format_decimal(event['event_balance']),
                "txhash_balance": format_decimal(event['txhash_balance'])
            }
            formatted_events.append(formatted_event)
      
        formatted_rewards = []
        for reward in rewards:
            formatted_reward = {
                "provider": normalize_address(reward['provider']),
                "weighted_avg_liquidity": format_decimal(reward['weighted_avg_liquidity']),
                "estimated_reward_in_arb_tokens": format_decimal(reward['estimated_reward_in_arb_tokens']),
                "estimated_reward_in_arb_usd": format_decimal(reward['estimated_reward_in_arb_usd']),
                "estimated_reward_in_t_usd": format_decimal(reward['estimated_reward_in_t_usd']),
                "estimated_reward_in_t_tokens": format_decimal(reward['estimated_reward_in_t_tokens'])
            }
            formatted_rewards.append(formatted_reward)
        
        formatted_data = {
            "total_weighted_liquidity": format_decimal(total_weighted_liquidity),
            "rewards": formatted_rewards,
            "events": formatted_events
        }

        return formatted_data
    except Exception as e:
        logger.error(f"Error formatting rewards data: {str(e)}", exc_info=True)
        raise