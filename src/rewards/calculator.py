import json
import os
from datetime import datetime
import logging
from src.config import START_DATE, END_DATE, TOTAL_REWARDS, HISTORICAL_PRICES_FILE
from src.utils.helpers import normalize_address, get_token_price, load_events

logger = logging.getLogger(__name__)

async def calculate_rewards():
    events = load_events()
    provider_liquidity = {}
    start_date = START_DATE
    end_date = END_DATE
    now_date = datetime.now()
    total_duration = (end_date - start_date).total_seconds()

    sorted_events = sorted(events, key=lambda x: (x['timestamp'], 0 if x['action'] == 'add' else 1))    
    
    for event in sorted_events:
        try:
            provider = event['args']['provider'] if 'provider' in event['args'] else event['args'].get('owner')
            if not provider:
                logger.warning(f"No provider found for event: {event}")
                continue

            event_timestamp = datetime.fromtimestamp(event['timestamp'])
            tokens = event['tokens']
            token0_info = tokens.get('token0', {})
            token1_info = tokens.get('token1', {})
            amounts = event['amounts']
            action = event['action']

            if len(amounts) < 2:
                logger.warning(f"Invalid amounts for event: {event}")
                continue

            token0_price = get_token_price(token0_info.get('coingecko_id'), event_timestamp, HISTORICAL_PRICES_FILE)
            token1_price = get_token_price(token1_info.get('coingecko_id'), event_timestamp, HISTORICAL_PRICES_FILE)
            convert_amount0_to_number = amounts[0] / 10**token0_info.get('decimals', 0)
            convert_amount1_to_number = amounts[1] / 10**token1_info.get('decimals', 0)
            total_value = (convert_amount0_to_number * token0_price) + (convert_amount1_to_number * token1_price)

            if provider not in provider_liquidity:
                provider_liquidity[provider] = []

            if action == "add":
                if provider_liquidity[provider]:
                    last_event = provider_liquidity[provider][-1]
                    new_amount = last_event[1] + total_value
                else:
                    new_amount = total_value
                provider_liquidity[provider].append((event_timestamp, new_amount))
            elif action == "remove":
                if provider_liquidity[provider]:
                    last_event = provider_liquidity[provider][-1]
                    new_amount = max(0, last_event[1] - total_value)
                    provider_liquidity[provider].append((event_timestamp, new_amount))
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}", exc_info=True)

    weighted_avg_liquidity = {}
    for provider, liquidity_events in provider_liquidity.items():
        if not liquidity_events:
            logger.warning(f"No liquidity events for address {normalize_address(provider)}")
            continue

        total_liquidity_time = 0
        for i in range(len(liquidity_events)):
            current_time, current_amount = liquidity_events[i]
            if start_date <= current_time <= end_date:
                current_time = start_date

            if i < len(liquidity_events) - 1:
                next_time = liquidity_events[i+1][0]
            else:
                next_time = now_date
            
            duration = (next_time - current_time).total_seconds()
            total_liquidity_time += current_amount * duration

        weighted_avg_liquidity[provider] = total_liquidity_time / total_duration

    total_weighted_liquidity = sum(weighted_avg_liquidity.values())
    rewards = []
    
    if total_weighted_liquidity > 0:
        for provider, avg_liquidity in weighted_avg_liquidity.items():
            provider_arb_reward_in_tokens = (avg_liquidity / total_weighted_liquidity) * TOTAL_REWARDS
            provider_arb_reward_in_usd = provider_arb_reward_in_tokens * get_token_price("arbitrum", event_timestamp, HISTORICAL_PRICES_FILE)
            provider_reward_in_t_usd = provider_arb_reward_in_usd * 0.25
            provider_reward_in_t_tokens = provider_reward_in_t_usd / get_token_price("threshold-network-token", event_timestamp, HISTORICAL_PRICES_FILE)
            rewards.append({
                "provider": provider.hex() if isinstance(provider, bytes) else provider,
                "weighted_avg_liquidity": avg_liquidity,
                "estimated_reward_in_arb_tokens": provider_arb_reward_in_tokens,
                "estimated_reward_in_arb_usd": provider_arb_reward_in_usd,
                "estimated_reward_in_t_usd": provider_reward_in_t_usd,
                "estimated_reward_in_t_tokens": provider_reward_in_t_tokens
            })
    else:
        logger.warning("Total weighted liquidity is zero, no rewards to distribute")

    return rewards