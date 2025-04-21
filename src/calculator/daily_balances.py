import json
import logging
from datetime import datetime, timedelta, timezone
from src.utils.helpers import get_token_price
from src.data.state_manager import load_state
from src.config import START_DATE, TOKENS

logger = logging.getLogger(__name__)

class DailyBalanceCalculator:
    def __init__(self, provider_balances_file, daily_balances_file):
        self.provider_balances_file = provider_balances_file
        self.daily_balances_file = daily_balances_file
        
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
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.daily_balances_file}: {e}")
            logger.error("File content might be corrupted. Starting with empty balances.")
            # Optional: Backup corrupted file?
            # Consider backing up the corrupted file here if needed
            # import shutil
            # backup_path = self.daily_balances_file + ".corrupted"
            # try:
            #     shutil.copy2(self.daily_balances_file, backup_path)
            #     logger.info(f"Backed up corrupted file to {backup_path}")
            # except Exception as backup_e:
            #     logger.error(f"Failed to backup corrupted file: {backup_e}")
            return {}

    def save_daily_balances(self, daily_balances):
        try:
            with open(self.daily_balances_file, 'r+') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError as e:
                     logger.error(f"Error decoding existing JSON in {self.daily_balances_file} during save: {e}")
                     logger.error("Overwriting corrupted file with new data.")
                     existing_data = {}

                for provider, data in daily_balances.items():
                    if provider in existing_data:
                        # Avoid duplicate entries if recalculating
                        existing_dates = {entry['balance_date'] for entry in existing_data[provider]['balances']}
                        new_entries = [entry for entry in data['balances'] if entry['balance_date'] not in existing_dates]
                        existing_data[provider]['balances'].extend(new_entries)
                    else:
                        existing_data[provider] = data
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
        current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

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
                    try:
                        token_identifier = TOKENS.get(token)
                        if token_identifier is None:
                            logger.warning(f"Token {token} not found in TOKENS configuration.")
                            continue
                        token_price = get_token_price(token_identifier, calculation_date)
                        usd_balance = balance * token_price if balance * token_price >= 0.01 else 0
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
        self.last_calculated_date = current_date

        self.daily_balances = self.load_daily_balances()

daily_balance_calculator = DailyBalanceCalculator(
    provider_balances_file='./data/balances/provider_balances.json',
    daily_balances_file='./data/balances/daily_balances.json',
)