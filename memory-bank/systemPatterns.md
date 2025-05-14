# System Patterns

## Architectural Patterns
- **API Service Pattern**: Flask API providing access to calculated rewards
- **Background Processing Pattern**: Asynchronous task execution via asyncio
- **Configuration Pattern**: Environment variable-based configuration
- **Logging Pattern**: Structured logging with file and console output
- **Data Persistence Pattern**: IPFS storage via Pinata

## Data Flow
1. Background process fetches liquidity events from blockchain
2. System calculates token prices and total value
3. Reward distribution is calculated based on weighted average liquidity
4. Results are stored on IPFS
5. API endpoints serve the latest calculated data

## Task Management
- Threading used to run Flask API alongside background processing
- Asyncio for non-blocking blockchain interactions

## Error Handling
- Logging mechanism for tracking errors
- File and console logging handlers

## Security Considerations
- API keys stored in environment variables
- No authentication mechanism visible in current implementation
- Should evaluate API endpoint security

## Scalability Considerations
- Asynchronous processing allows for non-blocking operations
- IPFS storage provides distributed data availability
- Consider rate limits for external API calls (CoinGecko, Pinata)

## Loyalty Program Pattern
- Tiered rewards based on liquidity provision
- Events tracked from multiple DeFi protocols (Curve, Uniswap V3)
- Time-based program with defined start date and duration 