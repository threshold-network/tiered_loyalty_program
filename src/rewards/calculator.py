import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.config import START_DATE, END_DATE, TOTAL_REWARDS, HISTORICAL_PRICES_FILE
from src.utils.helpers import normalize_address, get_token_price

logger = logging.getLogger(__name__)

class RewardsCalculator:
    def __init__(self, daily_balances_file: str, start_date: datetime, end_date: datetime, total_rewards: float):
        self.daily_balances_file = daily_balances_file
        self.start_date = start_date
        self.end_date = end_date
        self.total_rewards = total_rewards

    def load_daily_balances(self) -> Dict[str, Any]:
        try:
            with open(self.daily_balances_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Daily balances file not found: {self.daily_balances_file}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from file: {self.daily_balances_file}")
            return {}

    def calculate_weighted_avg_liquidity(self, provider_liquidity: Dict[str, Any]) -> Dict[str, float]:
        now_date = datetime.now(timezone.utc)
        total_duration = (self.end_date - self.start_date).total_seconds()
        weighted_avg_liquidity = {}

        for provider, liquidity_events in provider_liquidity.items():
            total_liquidity_time = 0
            for i, event in enumerate(liquidity_events['balances']):
                balance_date = datetime.fromisoformat(event['balance_date'])
                total_balance_usd = float(event['total_usd_balance'])

                if i < len(liquidity_events['balances']) - 1:
                    next_time = datetime.fromisoformat(liquidity_events['balances'][i+1]['balance_date'])
                else:
                    next_time = min(now_date, self.end_date)
        
                duration = (next_time - balance_date).total_seconds()
                total_liquidity_time += total_balance_usd * duration

            weighted_avg_liquidity[provider] = total_liquidity_time / total_duration

        return weighted_avg_liquidity

    def calculate_rewards(self, weighted_avg_liquidity: Dict[str, float]) -> List[Dict[str, Any]]:
        now_date = datetime.now(timezone.utc)
        total_weighted_liquidity = sum(weighted_avg_liquidity.values())
        rewards = []

        if total_weighted_liquidity > 0:
            for provider, avg_liquidity in weighted_avg_liquidity.items():
                provider_arb_reward_in_tokens = (avg_liquidity / total_weighted_liquidity) * self.total_rewards
                provider_arb_reward_in_usd = provider_arb_reward_in_tokens * self.get_token_price("arbitrum", now_date)
                provider_reward_in_t_usd = provider_arb_reward_in_usd * 0.25
                provider_reward_in_t_tokens = provider_reward_in_t_usd / self.get_token_price("threshold-network-token", now_date)
                
                rewards.append({
                    "provider": normalize_address(provider),
                    "weighted_avg_liquidity": avg_liquidity,
                    "estimated_reward_in_arb_tokens": provider_arb_reward_in_tokens,
                    "estimated_reward_in_arb_usd": provider_arb_reward_in_usd,
                    "estimated_reward_in_t_usd": provider_reward_in_t_usd,
                    "estimated_reward_in_t_tokens": provider_reward_in_t_tokens
                })
        else:
            logger.warning("Total weighted liquidity is zero, no rewards to distribute")

        return rewards

    def get_token_price(self, token: str, date: datetime) -> float:
        try:
            return get_token_price(token, date, HISTORICAL_PRICES_FILE)
        except Exception as e:
            logger.error(f"Error getting token price for {token}: {str(e)}")
            return 0

    def run(self) -> Dict[str, Any]:
        try:
            provider_liquidity = self.load_daily_balances()
            weighted_avg_liquidity = self.calculate_weighted_avg_liquidity(provider_liquidity)
            rewards = self.calculate_rewards(weighted_avg_liquidity)

            return {
                "total_weighted_liquidity": sum(weighted_avg_liquidity.values()),
                "rewards": rewards,
            }
        except Exception as e:
            logger.error(f"Error calculating rewards: {str(e)}")
            return {"error": str(e)}

def calculate_rewards() -> Dict[str, Any]:
    calculator = RewardsCalculator(
        daily_balances_file='./data/balances/daily_balances.json',
        start_date=START_DATE,
        end_date=END_DATE,
        total_rewards=TOTAL_REWARDS
    )
    return calculator.run()