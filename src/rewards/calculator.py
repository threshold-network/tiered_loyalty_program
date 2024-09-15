from datetime import datetime, timezone
import logging
from src.config import START_DATE, END_DATE, TOTAL_REWARDS, HISTORICAL_PRICES_FILE
from src.utils.helpers import normalize_address, get_token_price, load_events, sort_events

logger = logging.getLogger(__name__)

async def calculate_rewards():
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    provider_txhash_balances = {}
    provider_liquidity = {}
    weighted_avg_liquidity = {}
    rewards = []
    
    start_date = START_DATE
    end_date = END_DATE
    now_date = datetime.now(timezone.utc)
    total_duration = (end_date - start_date).total_seconds()

    grouped_events = {}
    for event in events:
        provider = event.get('provider')
        if provider not in grouped_events:
            grouped_events[provider] = []
        grouped_events[provider].append(event)

    for provider, events in grouped_events.items():
        if provider not in provider_txhash_balances:
            provider_txhash_balances[provider] = {}
        if provider not in provider_liquidity:
            provider_liquidity[provider] = []

        balance_amount = 0
        txhash_counter = 0

        sorted_events = sorted(events, key=sort_events)

        for event in sorted_events:
            event_date = datetime.fromtimestamp(event.get('timestamp'), tz=timezone.utc)
            tokens = event.get('tokens')
            token0_info = tokens.get('token0')
            token1_info = tokens.get('token1')
            amounts = event.get('amounts')
            action = event.get('action')
            txhash = event.get('transactionHash')

            if txhash is None:
                logger.warning(f"Event missing transactionHash: {event} for provider {normalize_address(provider)}")
                continue

            if len(amounts) < 2:
                logger.warning(f"Invalid amounts for event: {event}")
                continue

            token0_price = get_token_price(token0_info.get('coingecko_id'), event_date, HISTORICAL_PRICES_FILE)
            token1_price = get_token_price(token1_info.get('coingecko_id'), event_date, HISTORICAL_PRICES_FILE)

            convert_amount0_to_number = amounts[0] / 10**token0_info.get('decimals', 0)
            convert_amount1_to_number = amounts[1] / 10**token1_info.get('decimals', 0)
            
            total_value = (convert_amount0_to_number * token0_price) + (convert_amount1_to_number * token1_price)
            
            if txhash not in provider_txhash_balances[provider]:
                provider_txhash_balances[provider][txhash] = {}
                txhash_counter = 0

            if event_date < start_date:
                if action == "add":
                    balance_amount += total_value
                elif action == "remove":
                    balance_amount = max(0, balance_amount - total_value)
                provider_txhash_balances[provider][txhash] = (balance_amount, start_date)
                
                event_copy = event.copy()
                event_copy['event_balance'] = balance_amount
                event_copy['txhash_counter'] = 9999
                if provider_liquidity[provider]:
                    provider_liquidity[provider][0] = event_copy
                else:
                    provider_liquidity[provider].append(event_copy)
            elif event_date >= start_date:
                txhash_counter += 1
                if action == "add":
                    balance_amount += total_value
                elif action == "remove":
                    balance_amount = max(0, balance_amount - total_value)
                provider_txhash_balances[provider][txhash] = (balance_amount, event_date)

                event_copy = event.copy()
                event_copy['event_balance'] = balance_amount
                event_copy['txhash_counter'] = txhash_counter
                provider_liquidity[provider].append(event_copy)
    
    for provider in provider_liquidity.keys():
        if provider not in provider_txhash_balances:
            logger.warning(f"Provider {provider} not found in provider_txhash_balances")
            continue

        txhash_balances = provider_txhash_balances[provider]
        
        for i, event in enumerate(provider_liquidity[provider]):
            txhash = event.get('transactionHash')
            if txhash is None:
                logger.warning(f"Event missing transactionHash for provider {normalize_address(provider)}: {event}")
                continue

            if txhash in txhash_balances:
                balance, date = txhash_balances[txhash]
                provider_liquidity[provider][i]['hash_balance_date'] = date
                provider_liquidity[provider][i]['hash_balance'] = balance
            else:
                logger.warning(f"No matching balance found for txhash {txhash} (provider {normalize_address(provider)})")
      
    logger.info(f"Total number of events (after start date): {sum(len(events) for events in provider_liquidity.values())}")
    
    for provider, liquidity_events in provider_liquidity.items():
        if not liquidity_events:
            logger.warning(f"No liquidity events for address {normalize_address(provider)}")
            continue

        total_liquidity_time = 0
        for i in range(len(liquidity_events)):
            hash_balance_date = liquidity_events[i].get('hash_balance_date')
            hash_balance = liquidity_events[i].get('hash_balance')

            if i < len(liquidity_events) - 1:
                next_time = liquidity_events[i+1].get('hash_balance_date')
            else:
                next_time = now_date
        
            duration = (next_time - hash_balance_date).total_seconds()
            total_liquidity_time += hash_balance * duration

        weighted_avg_liquidity[provider] = total_liquidity_time / total_duration

    total_weighted_liquidity = sum(weighted_avg_liquidity.values())
    
    if total_weighted_liquidity > 0:
        for provider, avg_liquidity in weighted_avg_liquidity.items():
            provider_arb_reward_in_tokens = (avg_liquidity / total_weighted_liquidity) * TOTAL_REWARDS
            provider_arb_reward_in_usd = provider_arb_reward_in_tokens * get_token_price("arbitrum", event_date, HISTORICAL_PRICES_FILE)
            provider_reward_in_t_usd = provider_arb_reward_in_usd * 0.25
            provider_reward_in_t_tokens = provider_reward_in_t_usd / get_token_price("threshold-network-token", event_date, HISTORICAL_PRICES_FILE)
            rewards_data = {
                "provider": provider.hex() if isinstance(provider, bytes) else provider,
                "weighted_avg_liquidity": avg_liquidity,
                "estimated_reward_in_arb_tokens": provider_arb_reward_in_tokens,
                "estimated_reward_in_arb_usd": provider_arb_reward_in_usd,
                "estimated_reward_in_t_usd": provider_reward_in_t_usd,
                "estimated_reward_in_t_tokens": provider_reward_in_t_tokens
            }
            rewards.append(rewards_data.copy())
    else:
        logger.warning("Total weighted liquidity is zero, no rewards to distribute")

    return {
        "total_weighted_liquidity": total_weighted_liquidity,
        "rewards": rewards,
        "events": {provider: events.copy() for provider, events in provider_liquidity.items()}
    }