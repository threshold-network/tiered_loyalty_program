# Tiered Loyalty Program

This project implements a tiered loyalty program for liquidity providers using Curve and Uniswap V3 pools on the Ethereum network. The system fetches and processes liquidity events, calculates rewards based on token prices, and logs the data to IPFS.

## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Files and Directories](#files-and-directories)
- [Contributing](#contributing)
- [License](#license)

## Overview
The tiered loyalty program rewards liquidity providers based on their weighted average liquidity. The system fetches events from Curve and Uniswap V3 pools, calculates the total value of tokens involved, and distributes rewards accordingly.

## Setup
1. **Set up a virtual environment:**
   ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

2. **Install dependencies:**
   ```sh
    pip install -r requirements.txt

3. **Configure environment variables:**
Create a .env file in the root directory and add the following:
   ```sh
    INFURA_KEY=your_infura_key
    PINATA_API_KEY=your_pinata_api_key
    PINATA_SECRET_API_KEY=your_pinata_secret_api_key
    TOTAL_REWARDS=1000
    START_DATE=2024-01-01T00:00:00
    PROGRAM_DURATION_WEEKS=12
    START_BLOCK=12000000

## Usage
1. **Run the Flask API:**

   ```sh
    python backend_service.py

2. **Access the API:**
- The Flask API will be available at http://localhost:5000.

## API Endpoints
- GET /api/latest-cids
    - Returns the latest CIDs for events and rewards logged to IPFS.

## Files and Directories

backend_service.py: Main script to fetch events, calculate rewards, and run the Flask API.
fetch_prices.py: Script to fetch historical token prices from CoinGecko.
abi/curve_abi.json: ABI file for Curve pools.
abi/univ3_abi.json: ABI file for Uniswap V3 pools.
requirements.txt: List of Python dependencies.
.env: Environment configuration file (not included in the repository).
