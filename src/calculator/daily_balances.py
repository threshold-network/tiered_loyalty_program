import json
import logging
from datetime import datetime, timedelta, timezone
from src.utils.helpers import get_token_price
from src.data.state_manager import load_state
from src.config import START_DATE

logger = logging.getLogger(__name__)

class DailyBalanceCalculator:
    def __init__(self, provider_balances_file, daily_balances_file, token_prices_file):
        self.provider_balances_file = provider_balances_file
        self.daily_balances_file = daily_balances_file
        self.token_prices_file = token_prices_file
        
        last_calculated_date = load_state().get('last_daily_balance_date', None)
        
        if last_calculated_date:
            try:
                self.last_calculated_date = datetime.fromisoformat(last_calculated_date)
            except ValueError as e:
                logger.error(f"Invalid date format for last_daily_balance_date: {last_calculated_date}. Setting to None.")
                self.last_calculated_date = None
        else:
            self.last_calculated_date = None
        
        self.daily_balances = {}

    def load_provider_balances(self):
        try:
            with open(self.provider_balances_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Provider balances file not found: {self.provider_balances_file}")
            return {}

    def load_daily_balances(self):
        try:
            with open(self.daily_balances_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info(f"Daily balances file not found. Starting with empty balances: {self.daily_balances_file}")
            return {}

    def save_daily_balances(self, daily_balances):
        try:
            with open(self.daily_balances_file, 'r+') as f:
                existing_data = json.load(f)
                existing_data.update(daily_balances)
                f.seek(0)
                json.dump(existing_data, f, indent=2)
                f.truncate()
        except FileNotFoundError:
            with open(self.daily_balances_file, 'w') as f:
                json.dump(daily_balances, f, indent=2)

    def get_start_date(self):
        state = load_state()
        last_calculated_date = state.get('last_daily_balance_date')
        if last_calculated_date is None:
            return START_DATE.replace(hour=0, minute=0, second=0, microsecond=0)
        return datetime.fromisoformat(last_calculated_date) + timedelta(days=1)

    def calculate_daily_balances(self):
        provider_balances = self.load_provider_balances()
        existing_daily_balances = self.load_daily_balances()
        start_date = self.get_start_date()
        current_date = datetime.now(timezone.utc)

        if start_date >= current_date:
            logger.info("No new daily balances to calculate.")
            self.daily_balances = existing_daily_balances
            return

        new_balances = {}
        for provider, events in provider_balances.items():
            if provider not in new_balances:
                new_balances[provider] = {'balances': []}

            provider_daily_balances = new_balances[provider]['balances']
            last_event = events[-1]

            calculation_date = start_date
            while calculation_date < current_date:
                token_usd_balance = {}
                total_usd_balance = 0

                for token, balance in last_event['total_token_balance'].items():
                    token_info = next((t for t in last_event['tokens'].values() if t['symbol'] == token), None)
                    if token_info:
                        try:
                            token_price = get_token_price(token_info['coingecko_id'], calculation_date, self.token_prices_file)
                            usd_balance = max(0, balance * token_price)
                            token_usd_balance[token] = usd_balance
                            total_usd_balance += usd_balance
                        except Exception as e:
                            logger.error(f"Error calculating USD balance for {token}: {str(e)}")

                daily_balance = {
                    'balance_date': calculation_date.isoformat(),
                    'token_usd_balance': token_usd_balance,
                    'total_usd_balance': total_usd_balance
                }

                provider_daily_balances.append(daily_balance)

                calculation_date += timedelta(days=1)

        self.save_daily_balances(new_balances)
        self.last_calculated_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)

        existing_daily_balances.update(new_balances)
        self.daily_balances = existing_daily_balances

daily_balance_calculator = DailyBalanceCalculator(
    provider_balances_file='./data/balances/provider_balances.json',
    daily_balances_file='./data/balances/daily_balances.json',
    token_prices_file='./data/token_historical_prices.json'
)