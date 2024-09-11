import json
import os
from web3 import Web3
import logging
from src.blockchain.web3_client import web3_client
from src.config import END_TIMESTAMP
from src.utils.helpers import get_event_abi, create_event_signature, decode_log, get_ordered_token_amounts, get_tokens_from_contract

logger = logging.getLogger(__name__)

class EventFetcher:
    def __init__(self):
        self.w3 = web3_client.w3

    async def fetch_and_save_events(self, pools, from_block, to_block):
        all_new_events = []
        for pool in pools:
            events = await self.fetch_events(pool, from_block, to_block)
            all_new_events.extend(events)

        if all_new_events:
            self.save_events(all_new_events)

        return all_new_events

    async def fetch_events(self, pool, from_block, to_block):
        contract = self.w3.eth.contract(address=pool["address"], abi=pool["abi"])
        events = []

        logger.info(f"Processing blocks from {from_block} to {to_block} for pool {pool['address']}")

        try:
            event_names = pool.get("events", [])
            token0, token1 = get_tokens_from_contract(self.w3, pool)

            for event_name in event_names:
                event_abi = get_event_abi(contract, event_name)
                if not event_abi:
                    logger.warning(f"Event {event_name} not found in ABI for pool {pool['address']}")
                    continue

                event_signature = create_event_signature(event_abi)
                if not event_signature:
                    logger.warning(f"Could not create signature for event {event_name}")
                    continue

                event_signature_hash = Web3.keccak(text=event_signature).hex()

                logs = self.w3.eth.get_logs({
                    'fromBlock': from_block,
                    'toBlock': to_block,
                    'address': pool["address"],
                    'topics': [event_signature_hash]
                })
                
                logger.info(f"Fetched {len(logs)} {event_name} events for pool {pool['address']}")
                
                for log in logs:
                    try:
                        block = self.w3.eth.get_block(log['blockNumber'])
                        event_timestamp = block['timestamp']
                        if int(pool["deploy_date"].timestamp()) <= event_timestamp <= END_TIMESTAMP:
                            decoded_event = decode_log(event_abi, log)
                            decoded_event['timestamp'] = event_timestamp
                            decoded_event['transactionHash'] = log['transactionHash'].hex()
                            decoded_event['pool_address'] = pool["address"]
                            if token0 and token1:
                                decoded_event['tokens'] = {"token0": token0, "token1": token1}
                            else:
                                logger.warning(f"Unable to get token information for pool {pool['address']}")
                                continue
                            amounts = get_ordered_token_amounts(decoded_event)
                            decoded_event['amounts'] = amounts
                            event_type = decoded_event['event']
                            if event_type in ["AddLiquidity", "Mint"]:
                                decoded_event['action'] = "add"
                            elif event_type in ["RemoveLiquidity", "RemoveLiquidityImbalance", "RemoveLiquidityOne", "Burn"]:
                                decoded_event['action'] = "remove"
                            else:
                                decoded_event['action'] = "unknown"
                                logger.warning(f"Unknown event type: {event_type}")
                                continue

                            # Convert any remaining hex-like objects to strings
                            decoded_event = self._convert_to_serializable(decoded_event)

                            events.append(decoded_event)
                    except Exception as e:
                        logger.error(f"Error processing event: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to fetch events for pool {pool['address']}: {str(e)}")

        logger.info(f"Total events eligible for rewards on pool {pool['address']}: {len(events)}")
        return events

    def _convert_to_serializable(self, obj):
        if isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(v) for v in obj]
        elif hasattr(obj, 'hex'):
            return obj.hex()
        else:
            return obj

    def save_events(self, new_events):
        file_path = os.path.join('data', 'pools_events.json')
        try:
            with open(file_path, 'r+') as f:
                try:
                    existing_events = json.load(f)
                except json.JSONDecodeError:
                    existing_events = []
                
                existing_events.extend(new_events)
                f.seek(0)
                json.dump(existing_events, f)
                f.truncate()
        except FileNotFoundError:
            with open(file_path, 'w') as f:
                json.dump(new_events, f)

        logger.info(f"Saved {len(new_events)} new events to {file_path}")

event_fetcher = EventFetcher()