# Tiered Loyalty Program

This project implements a tiered loyalty program for liquidity providers using Curve and Uniswap V3 pools on the Arbitrum network. The system fetches and processes liquidity events, calculates rewards based on token prices, and provides API access to the calculated data.

## Project Status: COMPLETED ✅
This project has been successfully completed and archived. All core features have been implemented, and the system is fully operational. The most recent update ensures rewards are calculated consistently using the program end date.

## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Files and Directories](#files-and-directories)
- [Key Features](#key-features)
- [Contributing](#contributing)
- [License](#license)
- [MERKL Airdrop Processing](#merkl-airdrop-processing)

## Overview
The tiered loyalty program rewards liquidity providers based on their time-weighted average liquidity. The system fetches events from Curve and Uniswap V3 pools, calculates the total value of tokens involved, and distributes rewards proportionally. Rewards calculation respects the program's start and end dates for consistency. The backend runs an asynchronous loop for data processing and serves results via a Flask API.

## Setup
1. **Set up a virtual environment:**
   ```sh
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

2. **Install dependencies:**
   ```sh
    pip install -r requirements.txt
    ```

3. **Create required directories:**
   The application requires `logs` and `data/balances` directories.
   ```sh
    mkdir -p logs data/balances
    ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory and add the following variables. Get API keys and RPC URLs from the respective services.
   ```dotenv
   # Required
   ALCHEMY_URL=your_arbitrum_alchemy_https_url # Recommended RPC endpoint
   COINGECKO_API_KEY=your_coingecko_api_key # Optional for CoinGecko API
   TOTAL_REWARDS=50000                # Total rewards to distribute (in ARB tokens)
   START_DATE=2024-09-09T00:00:00     # Program start date in ISO format (UTC)
   PROGRAM_DURATION_WEEKS=30          # Duration of the program in weeks
   
   # Optional
   INFURA_KEY=your_arbitrum_infura_key      # Fallback RPC if ALCHEMY_URL is not set
   PORT=5001                            # Port for the Flask API (defaults to 5000)
   ```

## Usage
1. **Run the application:**
   This starts both the background processing loop and the Flask API.
   ```sh
    python3 run.py
    ```

2. **Access the API:**
   - The Flask API will be available at `http://localhost:<PORT>` (defaulting to `http://localhost:5000`).

## API Endpoints
- `GET /api/get_latest_rewards`
    - Returns the latest calculated rewards and liquidity data.
    - Includes calculation date, program start/end dates, and detailed reward distribution.

## Files and Directories
- `run.py`: Main entry point script. Starts the background processing loop and the Flask API.
- `src/`: Contains the core application logic.
    - `app.py`: Defines the Flask application and background task management.
    - `config.py`: Loads configuration from environment variables and defines constants.
    - `blockchain/`: Contains blockchain interaction components.
      - `event_fetcher.py`: Fetches and processes blockchain events from pools.
      - `web3_client.py`: Provides Web3 connectivity with retry and fallback mechanisms.
    - `calculator/`: Contains the calculation logic.
      - `balances.py`: Processes liquidity balances data.
      - `daily_balances.py`: Aggregates balances on a daily basis.
      - `rewards.py`: Calculates time-weighted rewards distribution.
    - `data/`: Data processing and state management.
    - `utils/`: Helper functions and utilities.
- `abi/`: Contains ABI JSON files for interacting with smart contracts.
- `data/`: Stores application state and cached data.
  - `balances/`: Stores daily balances information.
  - `token_historical_prices.json`: Cached token price data.
- `logs/`: Stores application logs.
- `docs/archive/`: Contains the project archive documentation.
- `requirements.txt`: List of Python dependencies.
- `.env`: Environment configuration file (not included in the repository).

## Key Features
- **Time-Weighted Average Liquidity Calculation**: Rewards are based on the weighted average liquidity provided over time.
- **Multi-Protocol Support**: Fetches data from both Curve and Uniswap V3 pools.
- **Proper End Date Handling**: All calculations respect the program's end date (April 7th, 2025).
- **Token Price Integration**: Uses CoinGecko API to fetch current and historical token prices.
- **Resilient RPC Connectivity**: Implements fallback mechanisms and retry logic for blockchain interactions.
- **Comprehensive API**: Provides detailed reward and liquidity data through a REST API.

## Contributing
This project is complete, but contributions for maintenance or enhancements are welcome. Please contact the repository owner for more information.

## License
(Placeholder for license information)

## MERKL Airdrop Processing

This project includes tools for processing reward data for MERKL airdrops. These tools allow you to:

1. Validate reward calculations
2. Convert rewards to MERKL format for both ARB and T tokens
3. Validate MERKL format files before submission

### Processing Workflow

```bash
# Step 1: Validate the rewards file
python src/utils/rewards_validator.py data/rewards/rewards_20250514_165141.json

# Step 2: Convert rewards to MERKL format
python src/utils/merkl_converter.py data/rewards/rewards_20250514_165141.json --output-dir data/merkl

# Step 3: Validate the MERKL format files
python src/utils/merkl_validator.py --pair data/merkl/rewards_20250514_165141_merkl_arb.json data/merkl/rewards_20250514_165141_merkl_t.json

# Alternative: Process everything at once
python src/utils/merkl_processor.py data/rewards/rewards_20250514_165141.json --output-dir data/merkl
```

For more details on the MERKL processing tools, see [MERKL Tools Documentation](src/utils/README.md).
