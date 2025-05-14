#!/usr/bin/env python3
"""
Technology Validation Script for Tiered Loyalty Program

This script validates the key technology components:
1. Python environment and dependencies
2. Web3 connection to Arbitrum
3. CoinGecko API access
4. Basic reward calculation logic
"""

import os
import sys
import json
import asyncio
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("tech_validation")

# Status tracking
validation_results = {
    "python_environment": False,
    "dependencies": False,
    "web3_connection": False,
    "coingecko_api": False,
    "basic_calculation": False,
    "overall_status": False
}

def validate_environment():
    """Validate Python environment and dependencies"""
    try:
        import flask
        import web3
        import dotenv
        import aiohttp
        
        logger.info(f"✅ Python version: {sys.version}")
        logger.info(f"✅ Flask version: {flask.__version__}")
        logger.info(f"✅ Web3 version: {web3.__version__}")
        logger.info("✅ Dependencies validated successfully")
        validation_results["python_environment"] = True
        validation_results["dependencies"] = True
        return True
    except ImportError as e:
        logger.error(f"❌ Dependency validation failed: {str(e)}")
        return False

async def validate_web3_connection():
    """Validate Web3 connection to Arbitrum"""
    try:
        from web3 import Web3
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Check for RPC URL
        rpc_url = os.getenv("ALCHEMY_URL")
        if not rpc_url:
            infura_key = os.getenv("INFURA_KEY")
            if infura_key:
                rpc_url = f"https://arbitrum-mainnet.infura.io/v3/{infura_key}"
            else:
                logger.error("❌ No RPC URL found in environment variables")
                return False
        
        # Create Web3 connection
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Check connection by trying to get the latest block number
        try:
            block_number = w3.eth.block_number
            logger.info(f"✅ Connected to Arbitrum. Current block: {block_number}")
            validation_results["web3_connection"] = True
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Arbitrum: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"❌ Web3 connection validation failed: {str(e)}")
        return False

async def validate_coingecko_api():
    """Validate CoinGecko API access"""
    try:
        import aiohttp
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Check for CoinGecko API key
        api_key = os.getenv("COINGECKO_API_KEY", "")
        
        # Test connection with the simple ping endpoint
        async with aiohttp.ClientSession() as session:
            # Using /ping endpoint which doesn't require authentication
            url = "https://api.coingecko.com/api/v3/ping"
            headers = {}
            if api_key:
                headers = {"X-CG-Pro-API-Key": api_key}
            
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Connected to CoinGecko API: {data}")
                        validation_results["coingecko_api"] = True
                        return True
                    else:
                        # Try alternative endpoint if /ping fails
                        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
                        async with session.get(url, headers=headers) as alt_response:
                            if alt_response.status == 200:
                                data = await alt_response.json()
                                logger.info(f"✅ Connected to CoinGecko API with alternative endpoint")
                                validation_results["coingecko_api"] = True
                                return True
                            else:
                                logger.error(f"❌ Failed to connect to CoinGecko API. Status: {alt_response.status}")
                                return False
            except Exception as e:
                logger.error(f"❌ Failed API request to CoinGecko: {str(e)}")
                return False
    except Exception as e:
        logger.error(f"❌ CoinGecko API validation failed: {str(e)}")
        return False

def validate_basic_calculation():
    """Validate basic reward calculation logic"""
    try:
        # Sample data
        total_rewards = 50000
        providers = {
            "provider1": {"liquidity": 1000, "days": 30},
            "provider2": {"liquidity": 2000, "days": 15},
            "provider3": {"liquidity": 500, "days": 60}
        }
        
        # Calculate weighted liquidity
        weighted_liquidity = {}
        total_weighted = 0
        
        for provider, data in providers.items():
            weighted = data["liquidity"] * data["days"]
            weighted_liquidity[provider] = weighted
            total_weighted += weighted
        
        # Calculate rewards
        rewards = {}
        for provider, weighted in weighted_liquidity.items():
            reward = (weighted / total_weighted) * total_rewards
            rewards[provider] = reward
        
        # Validate results
        total_distributed = sum(rewards.values())
        if abs(total_distributed - total_rewards) < 0.01:
            logger.info(f"✅ Basic reward calculation validated. Total distributed: {total_distributed}")
            validation_results["basic_calculation"] = True
            return True
        else:
            logger.error(f"❌ Basic calculation failed. Expected: {total_rewards}, Got: {total_distributed}")
            return False
    except Exception as e:
        logger.error(f"❌ Basic calculation validation failed: {str(e)}")
        return False

def print_validation_summary():
    """Print validation summary"""
    print("\n" + "=" * 50)
    print("TECHNOLOGY VALIDATION SUMMARY")
    print("=" * 50)
    
    validation_results["overall_status"] = all([
        validation_results["python_environment"],
        validation_results["dependencies"],
        validation_results["web3_connection"],
        validation_results["coingecko_api"],
        validation_results["basic_calculation"]
    ])
    
    status_symbols = {True: "✅", False: "❌"}
    
    print(f"{status_symbols[validation_results['python_environment']]} Python Environment")
    print(f"{status_symbols[validation_results['dependencies']]} Dependencies")
    print(f"{status_symbols[validation_results['web3_connection']]} Web3 Connection")
    print(f"{status_symbols[validation_results['coingecko_api']]} CoinGecko API")
    print(f"{status_symbols[validation_results['basic_calculation']]} Basic Calculation")
    
    print("\n" + "-" * 50)
    print(f"OVERALL STATUS: {status_symbols[validation_results['overall_status']]} {'PASSED' if validation_results['overall_status'] else 'FAILED'}")
    print("=" * 50)
    
    # Save results to file
    with open('tech_validation_results.json', 'w') as f:
        json.dump({
            "results": validation_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    logger.info(f"Validation results saved to tech_validation_results.json")

async def run_validations():
    """Run all validations"""
    env_valid = validate_environment()
    if not env_valid:
        logger.error("❌ Environment validation failed, aborting other checks")
        return
    
    # Run validations concurrently
    web3_task = validate_web3_connection()
    coingecko_task = validate_coingecko_api()
    
    await asyncio.gather(web3_task, coingecko_task)
    
    # Run calculation validation
    validate_basic_calculation()
    
    # Print summary
    print_validation_summary()

if __name__ == "__main__":
    logger.info("Starting technology validation")
    asyncio.run(run_validations()) 