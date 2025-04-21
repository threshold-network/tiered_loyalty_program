# Loyalty Program

This project implements a tiered loyalty program for liquidity providers using Curve and Uniswap V3 pools on the Arbitrum network. The system fetches and processes liquidity events, calculates rewards based on token prices, and logs the data to IPFS.

## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Files and Directories](#files-and-directories)
- [Contributing](#contributing)
- [License](#license)

## Overview
The tiered loyalty program rewards liquidity providers based on their weighted average liquidity. The system fetches events from Curve and Uniswap V3 pools, calculates the total value of tokens involved, and distributes rewards accordingly. The backend runs an asynchronous loop for data processing and serves results via a Flask API.

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

3. **Create logs directory:**
   The application requires a `logs` directory for its log files.
   ```sh
    mkdir logs
    ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory and add the following variables. Get API keys and RPC URLs from the respective services.
   ```dotenv
   # Required
   ALCHEMY_URL=your_arbitrum_alchemy_https_url # Recommended RPC endpoint
   PINATA_API_KEY=your_pinata_api_key
   PINATA_SECRET_API_KEY=your_pinata_secret_api_key
   TOTAL_REWARDS=1000                 # Total rewards to distribute (e.g., in USD)
   START_DATE=2024-01-01T00:00:00     # Program start date in ISO format (UTC)
   PROGRAM_DURATION_WEEKS=12          # Duration of the program in weeks
   
   # Optional
   # INFURA_KEY=your_arbitrum_infura_key      # Fallback RPC if ALCHEMY_URL is not set
   # COINGECKO_API_KEY=your_coingecko_api_key # Optional Demo key for CoinGecko Public API
   # PORT=5001                            # Port for the Flask API (defaults to 5000)
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
    - Returns the latest calculated rewards and liquidity data as a JSON file.

## Files and Directories
- `run.py`: Main entry point script. Starts the background processing loop and the Flask API.
- `src/`: Contains the core application logic.
    - `app.py`: Defines the Flask application and background task management.
    - `config.py`: Loads configuration from environment variables and defines constants.
    - `data_processing.py`: Handles fetching events, calculating liquidity, and rewards.
    - `ipfs_utils.py`: Utilities for interacting with IPFS via Pinata.
    - `price_fetching.py`: Logic for fetching token prices (uses CoinGecko).
    - `utils/`: Helper functions and utilities.
    - `web3_utils.py`: Utilities for interacting with the blockchain via Web3.py.
- `abi/`: Contains ABI JSON files for interacting with smart contracts.
- `data/`: Stores application state and cached data (e.g., `program_state.json`, `token_historical_prices.json`). Created automatically if it doesn't exist.
- `logs/`: Stores application logs (e.g., `app.log`). Needs to be created manually.
- `requirements.txt`: List of Python dependencies.
- `.env`: Environment configuration file (not included in the repository).

## Contributing
(Placeholder for contribution guidelines)

## License
(Placeholder for license information)
