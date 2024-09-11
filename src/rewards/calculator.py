import json
import os
from datetime import datetime, timezone
import logging
from src.config import START_DATE, END_DATE, TOTAL_REWARDS, HISTORICAL_PRICES_FILE
from src.utils.helpers import normalize_address, get_token_price, load_events

logger = logging.getLogger(__name__)

async def calculate_rewards():
    events = load_events()
    provider_liquidity = {}
    provider_txhash_balances = {}
    start_date = START_DATE
    end_date = END_DATE
    now_date = datetime.now(timezone.utc)
    total_duration = (end_date - start_date).total_seconds()

    sorted_events = sorted(events, key=lambda x: (x['timestamp'], 0 if x['action'] == 'add' else 1))    
    
    formatted_events = []

    logger.info(f"Calculating rewards for {len(sorted_events)} events")
    
    for event in sorted_events:
        try:
            provider = event['args']['provider'] if 'provider' in event['args'] else event['args'].get('owner')
            if not provider:
                logger.warning(f"No provider found for event: {event}")
                continue

            event_date = datetime.fromtimestamp(event['timestamp'], tz=timezone.utc)    
            tokens = event['tokens']
            token0_info = tokens.get('token0', {})
            token1_info = tokens.get('token1', {})
            amounts = event['amounts']
            action = event['action']
            txhash = event['transactionHash']

            if len(amounts) < 2:
                logger.warning(f"Invalid amounts for event: {event}")
                continue

            token0_price = get_token_price(token0_info.get('coingecko_id'), event_date, HISTORICAL_PRICES_FILE)
            token1_price = get_token_price(token1_info.get('coingecko_id'), event_date, HISTORICAL_PRICES_FILE)
            convert_amount0_to_number = amounts[0] / 10**token0_info.get('decimals', 0)
            convert_amount1_to_number = amounts[1] / 10**token1_info.get('decimals', 0)
            total_value = (convert_amount0_to_number * token0_price) + (convert_amount1_to_number * token1_price)

            if provider not in provider_liquidity:
                provider_liquidity[provider] = []
                provider_txhash_balances[provider] = {}

            if event_date < start_date:
                # Accrue balance without registering events before start_date
                if not provider_liquidity[provider]:
                    provider_liquidity[provider] = [(event_date, 0)]
                last_event = provider_liquidity[provider][-1]
                new_amount = last_event[1] + total_value if action == "add" else max(0, last_event[1] - total_value)
                provider_liquidity[provider][-1] = (last_event[0], new_amount)
                
                # If this is the last event before start_date, register the balance at start_date
                next_event = next((e for e in sorted_events if e['timestamp'] > event['timestamp']), None)
                if next_event is None or datetime.fromtimestamp(next_event['timestamp'], tz=timezone.utc) >= start_date:
                    provider_liquidity[provider].append((start_date, new_amount))
                    provider_txhash_balances[provider][txhash] = new_amount
            else:
                # For events after start_date, register each add and remove event
                if action == "add":
                    new_amount = provider_liquidity[provider][-1][1] + total_value if provider_liquidity[provider] else total_value
                else:  # action == "remove"
                    new_amount = max(0, provider_liquidity[provider][-1][1] - total_value) if provider_liquidity[provider] else 0
                provider_liquidity[provider].append((event_date, new_amount))
                provider_txhash_balances[provider][txhash] = new_amount

            formatted_events.append({
                "event": event['event'],
                "action": action,
                "pool_address": event['pool_address'],
                "provider": provider,
                "timestamp": event['timestamp'],
                "transactionHash": txhash,
                "token0": {
                    "symbol": token0_info.get('symbol', ''),
                    "amount": amounts[0],
                    "decimals": token0_info.get('decimals', 0)
                },
                "token1": {
                    "symbol": token1_info.get('symbol', ''),
                    "amount": amounts[1],
                    "decimals": token1_info.get('decimals', 0)
                },
                "balance_date": provider_liquidity[provider][-1][0],
                "event_balance": new_amount,
            })
            
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}", exc_info=True)

    # Calculate final txhash_balance for each provider and transaction hash
    for provider, txhash_balances in provider_txhash_balances.items():
        sorted_txhashes = sorted(txhash_balances.keys(), key=lambda x: next(event['timestamp'] for event in formatted_events if event['transactionHash'] == x))
        cumulative_balance = 0
        for txhash in sorted_txhashes:
            cumulative_balance = txhash_balances[txhash]
            for event in formatted_events:
                if event['provider'] == provider and event['transactionHash'] == txhash:
                    event['txhash_balance'] = cumulative_balance

    weighted_avg_liquidity = {}
    for provider, liquidity_events in provider_liquidity.items():
        if not liquidity_events:
            logger.warning(f"No liquidity events for address {normalize_address(provider)}")
            continue

        total_liquidity_time = 0
        for i in range(len(liquidity_events)):
            current_time, current_amount = liquidity_events[i]

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
            provider_arb_reward_in_usd = provider_arb_reward_in_tokens * get_token_price("arbitrum", event_date, HISTORICAL_PRICES_FILE)
            provider_reward_in_t_usd = provider_arb_reward_in_usd * 0.25
            provider_reward_in_t_tokens = provider_reward_in_t_usd / get_token_price("threshold-network-token", event_date, HISTORICAL_PRICES_FILE)
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

    return {
        "total_weighted_liquidity": total_weighted_liquidity,
        "rewards": rewards,
        "events": formatted_events
    }