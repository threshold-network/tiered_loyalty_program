import json
import argparse
from decimal import Decimal


def validate_rewards_file(input_file):
    """
    Validate the rewards JSON file according to the specified requirements:
    1. Check if sum of weighted_avg_liquidity equals total_weighted_liquidity
    2. Sum all reward fields
    3. Check if ARB token sum is 50,000
    4. Check if T token USD value is 25% of ARB token USD value
    5. Calculate relative token prices
    """
    try:
        print(f"Reading rewards file: {input_file}")
        with open(input_file, 'r') as f:
            rewards_data = json.load(f)
        
        if 'rewards' not in rewards_data:
            raise ValueError("Invalid rewards file format: 'rewards' key not found")
        
        # Initialize counters
        sum_weighted_avg_liquidity = Decimal('0')
        sum_arb_tokens = Decimal('0')
        sum_arb_usd = Decimal('0')
        sum_t_tokens = Decimal('0')
        sum_t_usd = Decimal('0')
        
        # Process each reward entry in the list
        for reward_data in rewards_data["rewards"]:
            # Add to weighted avg liquidity sum
            weighted_avg_liquidity = Decimal(str(reward_data.get("weighted_avg_liquidity", 0)))
            sum_weighted_avg_liquidity += weighted_avg_liquidity
            
            # Add to token and USD sums
            sum_arb_tokens += Decimal(str(reward_data.get("estimated_reward_in_arb_tokens", 0)))
            sum_arb_usd += Decimal(str(reward_data.get("estimated_reward_in_arb_usd", 0)))
            sum_t_tokens += Decimal(str(reward_data.get("estimated_reward_in_t_tokens", 0)))
            sum_t_usd += Decimal(str(reward_data.get("estimated_reward_in_t_usd", 0)))
        
        # Get total weighted liquidity from file
        total_weighted_liquidity = Decimal(str(rewards_data.get("total_weighted_liquidity", 0)))
        
        # Calculate token prices
        arb_price = sum_arb_usd / sum_arb_tokens if sum_arb_tokens > 0 else Decimal('0')
        t_price = sum_t_usd / sum_t_tokens if sum_t_tokens > 0 else Decimal('0')
        
        # Calculate t_usd as percentage of arb_usd
        t_percentage = (sum_t_usd / sum_arb_usd * 100) if sum_arb_usd > 0 else Decimal('0')
        
        # Validation results
        validations = {
            "weighted_liquidity_match": {
                "result": abs(sum_weighted_avg_liquidity - total_weighted_liquidity) < Decimal('0.001'),
                "sum_weighted_avg_liquidity": float(sum_weighted_avg_liquidity),
                "total_weighted_liquidity": float(total_weighted_liquidity),
                "difference": float(abs(sum_weighted_avg_liquidity - total_weighted_liquidity))
            },
            "arb_tokens_sum": {
                "result": abs(sum_arb_tokens - Decimal('50000')) < Decimal('0.01'),
                "sum_arb_tokens": float(sum_arb_tokens),
                "expected": 50000,
                "difference": float(abs(sum_arb_tokens - Decimal('50000')))
            },
            "t_usd_percentage": {
                "result": abs(t_percentage - Decimal('25')) < Decimal('0.1'),
                "t_usd_percentage": float(t_percentage),
                "expected_percentage": 25,
                "difference": float(abs(t_percentage - Decimal('25')))
            },
            "token_sums": {
                "sum_arb_tokens": float(sum_arb_tokens),
                "sum_arb_usd": float(sum_arb_usd),
                "sum_t_tokens": float(sum_t_tokens),
                "sum_t_usd": float(sum_t_usd)
            },
            "token_prices": {
                "arb_price_usd": float(arb_price),
                "t_price_usd": float(t_price)
            }
        }
        
        # Print validation results
        print("\n=== VALIDATION RESULTS ===")
        
        print("\n1. Weighted Liquidity Check:")
        if validations["weighted_liquidity_match"]["result"]:
            print("✓ PASS: Sum of weighted_avg_liquidity matches total_weighted_liquidity")
        else:
            print("✗ FAIL: Sum of weighted_avg_liquidity does not match total_weighted_liquidity")
        print(f"  - Sum of weighted_avg_liquidity: {validations['weighted_liquidity_match']['sum_weighted_avg_liquidity']}")
        print(f"  - Total weighted liquidity: {validations['weighted_liquidity_match']['total_weighted_liquidity']}")
        print(f"  - Difference: {validations['weighted_liquidity_match']['difference']}")
        
        print("\n2. ARB Token Sum Check:")
        if validations["arb_tokens_sum"]["result"]:
            print("✓ PASS: Sum of ARB tokens is approximately 50,000")
        else:
            print("✗ FAIL: Sum of ARB tokens is not 50,000")
        print(f"  - Sum of ARB tokens: {validations['arb_tokens_sum']['sum_arb_tokens']}")
        print(f"  - Expected: 50,000")
        print(f"  - Difference: {validations['arb_tokens_sum']['difference']}")
        
        print("\n3. T Token USD Percentage Check:")
        if validations["t_usd_percentage"]["result"]:
            print("✓ PASS: T token USD value is approximately 25% of ARB token USD value")
        else:
            print("✗ FAIL: T token USD value is not 25% of ARB token USD value")
        print(f"  - T token USD percentage: {validations['t_usd_percentage']['t_usd_percentage']}%")
        print(f"  - Expected: 25%")
        print(f"  - Difference: {validations['t_usd_percentage']['difference']}%")
        
        print("\n4. Token Sums:")
        print(f"  - Sum of ARB tokens: {validations['token_sums']['sum_arb_tokens']}")
        print(f"  - Sum of ARB USD value: ${validations['token_sums']['sum_arb_usd']}")
        print(f"  - Sum of T tokens: {validations['token_sums']['sum_t_tokens']}")
        print(f"  - Sum of T USD value: ${validations['token_sums']['sum_t_usd']}")
        
        print("\n5. Token Prices:")
        print(f"  - ARB price: ${validations['token_prices']['arb_price_usd']} per token")
        print(f"  - T price: ${validations['token_prices']['t_price_usd']} per token")
        
        # Overall validation result
        all_passed = all([
            validations["weighted_liquidity_match"]["result"],
            validations["arb_tokens_sum"]["result"],
            validations["t_usd_percentage"]["result"]
        ])
        
        print("\n=== OVERALL RESULT ===")
        if all_passed:
            print("✓ PASS: All validations passed")
        else:
            print("✗ FAIL: Some validations failed")
        
        return validations
    
    except Exception as e:
        print(f"Error validating rewards file: {str(e)}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate rewards JSON file")
    parser.add_argument("input_file", help="Path to the rewards JSON file")
    
    args = parser.parse_args()
    
    validate_rewards_file(args.input_file) 