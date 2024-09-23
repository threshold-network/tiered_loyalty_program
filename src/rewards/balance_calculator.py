import json
import logging
from datetime import datetime, timezone
from src.config import POOLS
from src.utils.helpers import (
    normalize_address, get_token_price, load_events,
    sort_events
)
from src.data.state_manager import load_state

logger = logging.getLogger(__name__)

def datetime_to_str(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

class BalanceCalculator:
    def __init__(self):
        self.provider_liquidity = {}
        self.last_processed_timestamp = None

    def load_balance_state(self):
        state = load_state()
        self.last_processed_timestamp = state.get('last_balance_timestamp')
        if self.last_processed_timestamp is None:
            logger.info("No last balance timestamp found. Starting from the beginning.")

    def load_balances(self):
        try:
            with open('./data/balances/provider_balances.json', 'r') as f:
                self.provider_liquidity = json.load(f)
        except FileNotFoundError:
            logger.info("No existing balances file found. Starting with empty balances.")

    def save_balances(self):
        with open('./data/balances/provider_balances.json', 'w') as f:
            json.dump(self.provider_liquidity, f, indent=2, default=datetime_to_str)

    def calculate_balances(self):
        self.load_balance_state()
        self.load_balances()

        events = load_events()
        if not events:
            logger.warning("No events found. Skipping balance calculation.")
            return
        else:
            logger.info(f"Loaded {len(events)} events")

        if self.last_processed_timestamp is None:
            self.last_processed_timestamp = min(int(pool['deploy_date'].timestamp()) for pool in POOLS) - 1
        
        logger.info(f"Starting balance calculation from timestamp {self.last_processed_timestamp}")

        new_events = [e for e in events if e['timestamp'] > self.last_processed_timestamp]
        sorted_events = sorted(new_events, key=sort_events)

        if not sorted_events:
            logger.info("No events found. Skipping balance calculation.")
            return

        for event in sorted_events:
            provider = normalize_address(event['provider'])
            if provider not in self.provider_liquidity:
                self.provider_liquidity[provider] = []

            pool_address = event['pool_address']
            token0 = event['tokens']['token0']
            token1 = event['tokens']['token1']
            amounts = event['amounts']
            action = event['action']
            tx_event = event['event']   

            balance_entry = {
                'provider': provider,
                'timestamp': event['timestamp'],
                'event': tx_event,
                'action': action,
                'transactionHash': event['transactionHash'],
                'txhash_counter': len(self.provider_liquidity[provider]),
                'tokens': event['tokens'],
                'amounts': amounts,
                'balance_date': datetime.fromtimestamp(event['timestamp'], tz=timezone.utc),
                'pool_balances': {},
            }

            if not self.provider_liquidity[provider] or pool_address not in self.provider_liquidity[provider][-1].get('pool_balances', {}):
                balance_entry['pool_balances'][pool_address] = {'balance_tokens': [0, 0], 'balance_usd': 0}
            else:
                balance_entry['pool_balances'][pool_address] = self.provider_liquidity[provider][-1]['pool_balances'][pool_address].copy()

            token0_balance = balance_entry['pool_balances'][pool_address]['balance_tokens'][0]
            token1_balance = balance_entry['pool_balances'][pool_address]['balance_tokens'][1]

            if action == 'add':
                token0_balance += amounts[0] / 10**token0['decimals']
                token1_balance += amounts[1] / 10**token1['decimals']
            elif action == 'remove':
                token0_balance -= amounts[0] / 10**token0['decimals']
                token1_balance -= amounts[1] / 10**token1['decimals']

            balance_entry['pool_balances'][pool_address]['balance_tokens'] = [
                token0_balance,
                token1_balance
            ]

            token0_price = get_token_price(token0['coingecko_id'], balance_entry['balance_date'], './data/token_historical_prices.json')
            token1_price = get_token_price(token1['coingecko_id'], balance_entry['balance_date'], './data/token_historical_prices.json')
            
            balance_entry['pool_balances'][pool_address]['balance_usd'] = max(0, token0_balance * token0_price + token1_balance * token1_price)

            balance_entry['total_balance_usd'] = max(0, sum(float(pool['balance_usd']) for pool in balance_entry['pool_balances'].values()))

            self.provider_liquidity[provider].append(balance_entry)

        self.last_processed_timestamp = max(event['timestamp'] for event in sorted_events)
        self.save_balances()

        logger.info(f"Balances calculated up to timestamp {self.last_processed_timestamp}")

balance_calculator = BalanceCalculator()