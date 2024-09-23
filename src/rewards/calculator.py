import logging
import json
from datetime import datetime, timezone
from src.config import START_DATE, END_DATE, TOTAL_REWARDS, HISTORICAL_PRICES_FILE
from src.utils.helpers import normalize_address, get_token_price

logger = logging.getLogger(__name__)

async def calculate_rewards():
    with open('./data/balances/provider_balances.json', 'r') as f:
        provider_liquidity = json.load(f)

    start_date = START_DATE
    end_date = END_DATE
    now_date = datetime.now(timezone.utc)
    total_duration = (end_date - start_date).total_seconds()

    weighted_avg_liquidity = {}
    rewards = []

    for provider, liquidity_events in provider_liquidity.items():
        total_liquidity_time = 0
        for i in range(len(liquidity_events)):
            balance_date = datetime.fromisoformat(liquidity_events[i]['balance_date'])
            total_balance_usd = liquidity_events[i]['total_balance_usd']

            if i < len(liquidity_events) - 1:
                next_time = datetime.fromisoformat(liquidity_events[i+1]['balance_date'])
            else:
                next_time = now_date
        
            duration = (next_time - balance_date).total_seconds()
            total_liquidity_time += total_balance_usd * duration

        weighted_avg_liquidity[provider] = total_liquidity_time / total_duration

    total_weighted_liquidity = sum(weighted_avg_liquidity.values())
    
    if total_weighted_liquidity > 0:
        for provider, avg_liquidity in weighted_avg_liquidity.items():
            provider_arb_reward_in_tokens = (avg_liquidity / total_weighted_liquidity) * TOTAL_REWARDS
            provider_arb_reward_in_usd = provider_arb_reward_in_tokens * get_token_price("arbitrum", now_date, HISTORICAL_PRICES_FILE)
            provider_reward_in_t_usd = provider_arb_reward_in_usd * 0.25
            provider_reward_in_t_tokens = provider_reward_in_t_usd / get_token_price("threshold-network-token", now_date, HISTORICAL_PRICES_FILE)
            rewards_data = {
                "provider": normalize_address(provider),
                "weighted_avg_liquidity": avg_liquidity,
                "estimated_reward_in_arb_tokens": provider_arb_reward_in_tokens,
                "estimated_reward_in_arb_usd": provider_arb_reward_in_usd,
                "estimated_reward_in_t_usd": provider_reward_in_t_usd,
                "estimated_reward_in_t_tokens": provider_reward_in_t_tokens
            }
            rewards.append(rewards_data)
    else:
        logger.warning("Total weighted liquidity is zero, no rewards to distribute")

    return {
        "total_weighted_liquidity": total_weighted_liquidity,
        "rewards": rewards,
        "events": provider_liquidity
    }