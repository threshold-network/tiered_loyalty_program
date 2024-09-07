import pytest
from datetime import datetime, timedelta
from main import calculate_rewards, START_TIMESTAMP, END_TIMESTAMP
import json
import os

# Mock the fetch_token_price function
def mock_fetch_token_price(coingecko_id, date):
    return 1.0  # Return a fixed price for simplicity

# Patch the fetch_token_price function
@pytest.fixture(autouse=True)
def patch_fetch_token_price(monkeypatch):
    monkeypatch.setattr("main.fetch_token_price", mock_fetch_token_price)

def transform_event_format(event):
    return {
        'event': event['event'],
        'action': event['action'],
        'args': {'provider': event['provider']},
        'timestamp': event['timestamp'],
        'tokens': {
            'token0': {'coingecko_id': event['token0']['symbol'].lower(), 'decimals': event['token0']['decimals']},
            'token1': {'coingecko_id': event['token1']['symbol'].lower(), 'decimals': event['token1']['decimals']}
        },
        'amounts': [int(event['token0']['amount']), int(event['token1']['amount'])]
    }

def test_calculate_rewards():
    # Load sample events from JSON file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(current_dir, 'sample_events.json')
    
    with open(json_file_path, 'r') as file:
        sample_events = json.load(file)

    # Transform events to the old format
    transformed_events = [transform_event_format(event) for event in sample_events]

    # Call the function
    rewards = calculate_rewards(transformed_events)

    start_timestamp = datetime.fromtimestamp(START_TIMESTAMP)
    end_timestamp = datetime.fromtimestamp(END_TIMESTAMP)
    total_duration = (end_timestamp - start_timestamp).total_seconds()
    print(start_timestamp)
    print(end_timestamp)
    print(total_duration)

    # Assertions
    reward = rewards[0]
    assert reward['provider'] == '0x54b5569deC8A6A8AE61A36Fd34e5c8945810db8b'
    # previously calculated on the spreadsheet
    assert 5 < reward['weighted_avg_liquidity'] <= 6

