import logging
from src.utils.helpers import normalize_address, format_decimal, sort_events
from datetime import datetime

logger = logging.getLogger(__name__)

def format_rewards_data(data):
    try:
        total_weighted_liquidity = data['total_weighted_liquidity']
        rewards = data['rewards']
        provider_liquidity = data['events']

        all_events = [event for provider_events in provider_liquidity.values() for event in provider_events]
        all_events_sorted = sorted(all_events, key=sort_events)

        formatted_events = []
        formatted_rewards = []

        for event in all_events_sorted:
            formatted_event = {
                "event": event.get('event', ''),
                "action": event.get('action', ''),
                "transactionHash": event.get('transactionHash', ''),
                "txhash_counter": event.get('txhash_counter', 0),
                "timestamp": event.get('timestamp', 0),
                "provider": normalize_address(event.get('provider', '')),
                "pool_address": event.get('pool_address', ''),
                "token0": {
                    "symbol": event.get('tokens', {}).get('token0', {}).get('symbol', ''),
                    "amount": format_decimal(event.get('amounts', [0, 0])[0]),
                    "decimals": event.get('tokens', {}).get('token0', {}).get('decimals', 0)
                },
                "token1": {
                    "symbol": event.get('tokens', {}).get('token1', {}).get('symbol', ''),
                    "amount": format_decimal(event.get('amounts', [0, 0])[1]),
                    "decimals": event.get('tokens', {}).get('token1', {}).get('decimals', 0)
                },
                "event_balance": format_decimal(event.get('total_balance_usd', 0), 2),
                "hash_balance_date": int(datetime.fromisoformat(event['balance_date']).timestamp()),
            }
            formatted_events.append(formatted_event)

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
        
        formatted_json_data = {
            "total_weighted_liquidity": format_decimal(total_weighted_liquidity),
            "rewards": formatted_rewards,
            "events": formatted_events
        }

        return formatted_json_data
    except Exception as e:
        logger.error(f"Error formatting rewards data: {str(e)}", exc_info=True)
        raise