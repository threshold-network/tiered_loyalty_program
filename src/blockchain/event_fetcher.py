import json
import os
from web3 import Web3
import logging
from src.blockchain.web3_client import web3_client
from src.config import END_TIMESTAMP
from src.utils.helpers import (
    get_event_abi, create_event_signature, decode_log, 
    get_ordered_token_amounts, get_tokens_from_contract, 
    convert_to_serializable
)

logger = logging.getLogger(__name__)

# Define a reasonable chunk size for fetching logs
LOG_FETCH_CHUNK_SIZE = 1_000_000 # Use the requested chunk size

class EventFetcher:
    def __init__(self):
        self.w3 = web3_client.w3

    async def fetch_and_save_events(self, pools, from_block, to_block):
        new_events = []
        for pool in pools:
            events = await self.fetch_events(pool, from_block, to_block)
            new_events.extend(events)

        if new_events:
            self.save_events(new_events)

        return new_events

    async def fetch_events(self, pool, from_block, to_block):
        contract = self.w3.eth.contract(address=pool["address"], abi=pool["abi"])
        events = []
        total_range = to_block - from_block

        logger.info(f"Processing blocks from {from_block} to {to_block} (Range: {total_range}) for pool {pool['address']}")

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
                
                all_logs_for_event = [] # Store logs for the current event across chunks

                # --- Chunking Logic ---
                current_from = from_block
                while current_from <= to_block:
                    current_to = min(current_from + LOG_FETCH_CHUNK_SIZE - 1, to_block)
                    logger.info(f"Fetching {event_name} logs for chunk: {current_from} - {current_to} for pool {pool['address']}")

                    chunk_logs = web3_client.call_with_retry(self.w3.eth.get_logs, {
                        'fromBlock': current_from,
                        'toBlock': current_to,
                        'address': pool["address"],
                        'topics': [event_signature_hash]
                    })

                    # Handle case where retry mechanism returns None after max retries
                    if chunk_logs is None:
                        logger.error(f"Failed to fetch logs for chunk {current_from}-{current_to} for {event_name} on pool {pool['address']} after retries. Skipping this chunk.")
                        # Decide if we should stop processing this event entirely or just skip the chunk
                        # For now, we'll skip the chunk and continue to the next one
                    else:
                         all_logs_for_event.extend(chunk_logs)
                         logger.info(f"Fetched {len(chunk_logs)} logs in chunk {current_from}-{current_to}")

                    current_from = current_to + 1
                # --- End Chunking Logic ---

                logger.info(f"Fetched a total of {len(all_logs_for_event)} {event_name} events for pool {pool['address']} across all chunks.")
                
                # Process the fetched logs (accumulated from all chunks)
                for log in all_logs_for_event:
                    try:
                        # block = self.w3.eth.get_block(log['blockNumber'])
                        block = web3_client.call_with_retry(self.w3.eth.get_block, log['blockNumber'])
                        if block is None:
                            logger.error(f"Failed to get block {log['blockNumber']} after retries. Skipping event log.")
                            continue # Skip this specific log if block fetching failed
                            
                        event_timestamp = block['timestamp']
                        if int(pool["deploy_date"].timestamp()) <= event_timestamp <= END_TIMESTAMP:
                            # tx = self.w3.eth.get_transaction(log['transactionHash'])
                            tx = web3_client.call_with_retry(self.w3.eth.get_transaction, log['transactionHash'])
                            if tx is None:
                                logger.error(f"Failed to get transaction {log['transactionHash'].hex()} after retries. Skipping event log.")
                                continue # Skip this specific log if transaction fetching failed
                                
                            decoded_event = decode_log(event_abi, log)
                            
                            provider_from_args = decoded_event['args'].get('provider') or decoded_event['args'].get('owner')
                            tx_from = tx['from']
                            
                            if provider_from_args and provider_from_args.lower() == tx_from.lower():
                                decoded_event['provider'] = provider_from_args
                            else:
                                decoded_event['provider'] = tx_from

                            decoded_event['timestamp'] = event_timestamp
                            decoded_event['transactionHash'] = log['transactionHash']
                            decoded_event['_from'] = tx_from
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

                            decoded_event = convert_to_serializable(decoded_event)

                            events.append(decoded_event)
                    except Exception as e:
                        # Log error for specific event processing but continue loop
                        logger.error(f"Error processing individual event log {log.get('transactionHash', 'N/A').hex()}: {str(e)}") 
        except Exception as e:
            # Log error for fetching process of a specific pool but continue to next pool
            logger.error(f"Failed during overall event fetching process for pool {pool['address']}: {str(e)}") 

        logger.info(f"Finished processing pool {pool['address']}. Found {len(events)} eligible events.")
        return events

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