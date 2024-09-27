import json
import logging
from datetime import datetime
from src.config import POOLS
from src.utils.helpers import (
    normalize_address, load_events,
    sort_events
)
from src.data.state_manager import load_state
import copy  # Add this import at the top of the file

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
                'pool_address': pool_address,
                'pool_balances': {},
                'total_token_balance': {}
            }
            
            previous_pool_balances = copy.deepcopy(self.provider_liquidity[provider][-1]['pool_balances']) if self.provider_liquidity[provider] else {}
            balance_entry['pool_balances'] = previous_pool_balances

            if pool_address not in balance_entry['pool_balances']:
                balance_entry['pool_balances'][pool_address] = {'token_balance': {}}
            
            token0_balance = balance_entry['pool_balances'][pool_address]['token_balance'].get(token0['symbol'], 0)
            token1_balance = balance_entry['pool_balances'][pool_address]['token_balance'].get(token1['symbol'], 0)

            if action == 'add':
                token0_balance += amounts[0] / 10**token0['decimals']
                token1_balance += amounts[1] / 10**token1['decimals']
            elif action == 'remove':
                token0_balance -= amounts[0] / 10**token0['decimals']
                token1_balance -= amounts[1] / 10**token1['decimals']

            balance_entry['pool_balances'][pool_address]['token_balance'] = {
                token0['symbol']: token0_balance,
                token1['symbol']: token1_balance
            }

            total_token_balance = {}
            for pool_address, pool_data in balance_entry['pool_balances'].items():
                token_balance = pool_data.get('token_balance', {})
                for token_symbol, balance in token_balance.items():
                    if token_symbol in total_token_balance:
                        total_token_balance[token_symbol] += balance
                    else:
                        total_token_balance[token_symbol] = balance

            balance_entry['total_token_balance'] = total_token_balance

            self.provider_liquidity[provider].append(balance_entry)

        self.last_processed_timestamp = max(event['timestamp'] for event in sorted_events)
        self.save_balances()

        logger.info(f"Balances calculated up to timestamp {self.last_processed_timestamp}")

balance_calculator = BalanceCalculator()