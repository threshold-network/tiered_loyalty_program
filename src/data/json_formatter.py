import logging
from src.utils.helpers import normalize_address, format_decimal, sort_events
from datetime import datetime

logger = logging.getLogger(__name__)

def format_rewards_data(data):
    try:
        total_weighted_liquidity = data['total_weighted_liquidity']
        rewards = data['rewards']
        provider_liquidity = data['provider_liquidity']
        daily_balances = data['daily_balances']

        formatted_provider_liquidity = format_provider_liquidity(provider_liquidity)
        formatted_daily_balances = format_daily_balances(daily_balances)
        formatted_rewards = format_rewards(rewards)

        formatted_json_data = {
            "total_weighted_liquidity": format_decimal(total_weighted_liquidity),
            "rewards": formatted_rewards,
            "provider_liquidity": formatted_provider_liquidity,
            "daily_balances": formatted_daily_balances
        }

        return formatted_json_data
    except Exception as e:
        logger.error(f"Error formatting rewards data: {str(e)}", exc_info=True)
        raise

def format_provider_liquidity(provider_liquidity):
    formatted_provider_liquidity = {}
    for provider, events in provider_liquidity.items():
        formatted_events = []
        for event in events:
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
                "pool_balances": event.get('pool_balances', {})
            }
            formatted_events.append(formatted_event)
        formatted_provider_liquidity[provider] = formatted_events
    return formatted_provider_liquidity

def format_daily_balances(daily_balances):
    formatted_daily_balances = {}
    for provider, balances in daily_balances.items():
        formatted_balances = []
        for balance in balances['balances']:
            formatted_balance = {
                "balance_date": balance['balance_date'],
                "token_usd_balance": {k: format_decimal(v) for k, v in balance['token_usd_balance'].items()},
                "total_usd_balance": format_decimal(balance['total_usd_balance'])
            }
            formatted_balances.append(formatted_balance)
        formatted_daily_balances[provider] = formatted_balances
    return formatted_daily_balances

def format_rewards(rewards):
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
    return formatted_rewards