# Tiered Loyalty Program - Project Brief

## Project Overview
This project implements a tiered loyalty program for liquidity providers using Curve and Uniswap V3 pools on the Arbitrum network. The system fetches and processes liquidity events, calculates rewards based on token prices, and logs the data to IPFS.

## Core Requirements
- Fetch events from Curve and Uniswap V3 pools on Arbitrum
- Calculate rewards based on weighted average liquidity
- Store data on IPFS via Pinata
- Provide API endpoints to access reward data
- Run asynchronous background processing

## Technical Stack
- Python 3.x
- Flask for API
- Web3.py for blockchain interactions
- Pinata for IPFS storage
- CoinGecko for price data
- Environment variables for configuration

## Project Duration
- Start Date: 2024-09-09
- Duration: 30 weeks

## Reward Structure
- Total Rewards: 50,000 (base currency)
- Distribution based on tiered loyalty system

## Key Files
- `run.py`: Main entry point
- `src/app.py`: Flask application and background task management
- `src/config.py`: Configuration from environment variables
- `src/blockchain/`: Blockchain interaction modules
- `src/calculator/`: Reward calculation logic
- `src/data/`: Data processing modules
- `src/utils/`: Helper functions and utilities 