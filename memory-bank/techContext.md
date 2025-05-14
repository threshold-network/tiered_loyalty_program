# Technical Context

## Development Environment
- Python 3.x
- Virtual environment (venv)
- macOS platform (darwin 24.4.0)

## Frameworks and Libraries
- Flask (3.0.3): Web framework for API
- Flask-Cors (3.0.10): Cross-origin resource sharing
- Web3.py (5.31.0): Ethereum/blockchain interaction
- python-dotenv (0.19.2): Environment variable management
- aiohttp: Asynchronous HTTP client/server
- asyncio (3.4.3): Asynchronous I/O
- pinatapy-vourhey (0.1.6): Pinata IPFS API client
- eth-abi (2.1.1) & eth-utils (1.10.0): Ethereum utilities
- pytest (7.1.2): Testing framework
- python-dateutil (2.8.2): Date utilities
- Werkzeug (3.0.4): WSGI web application library
- gunicorn (23.0.0): WSGI HTTP Server

## Configuration
- Environment variables stored in .env file
- Configuration parameters:
  - ALCHEMY_URL: Arbitrum RPC endpoint
  - INFURA_KEY: Backup Arbitrum RPC
  - PINATA_API_KEY & PINATA_SECRET_API_KEY: IPFS service
  - COINGECKO_API_KEY: Price data API
  - TOTAL_REWARDS: Total rewards to distribute
  - START_DATE: Program start date
  - PROGRAM_DURATION_WEEKS: Duration in weeks
  - PORT: API port (default 5000)

## Project Structure
- Main application entry: run.py
- Core modules in src/ directory:
  - app.py: Flask application and background tasks
  - config.py: Configuration loading and constants
  - blockchain/: Blockchain interaction modules
  - calculator/: Reward calculation logic
  - data/: Data processing modules
  - utils/: Helper utilities

## Data Storage
- IPFS via Pinata for distributed storage
- Local data/ directory for application state
- logs/ directory for application logs

## API Endpoints
- GET /api/get_latest_rewards: Returns latest calculated rewards 