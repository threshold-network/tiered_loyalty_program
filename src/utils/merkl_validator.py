import json
import os
import re
import argparse
from decimal import Decimal


def validate_ethereum_address(address):
    """Validate Ethereum address format."""
    pattern = re.compile(r'^0x[a-fA-F0-9]{40}$')
    return bool(pattern.match(address))


def validate_merkl_file(merkl_file, token_type=None):
    """
    Validate a MERKL format JSON file.
    
    Parameters:
    - merkl_file: Path to the MERKL format JSON file
    - token_type: "ARB" or "T" to validate specific token, None for any token
    
    Returns:
    - Dictionary with validation results
    """
    try:
        print(f"Validating MERKL file: {merkl_file}")
        
        with open(merkl_file, 'r') as f:
            data = json.load(f)
        
        # Define expected token addresses
        arb_token_address = "0xb50721bcf8d664c30412cfbc6cf7a15145234ad1"
        t_token_address = "0xcdf7028ceab81fa0c6971208e83fa7872994bee5"
        
        # Initialize validation results
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {
                "total_recipients": 0,
                "total_amount": Decimal('0'),
                "min_amount": None,
                "max_amount": Decimal('0'),
                "token_type": None,
            },
            "rewards": None  # Will store the rewards data for pair validation
        }
        
        # 1. Check file structure
        if "rewardToken" not in data:
            results["valid"] = False
            results["errors"].append("Missing 'rewardToken' field")
        
        if "rewards" not in data:
            results["valid"] = False
            results["errors"].append("Missing 'rewards' field")
            return results  # Can't continue validation without rewards field
        
        # Store rewards data for pair validation
        results["rewards"] = data.get("rewards", {})
        
        # 2. Validate token address
        token_address = data.get("rewardToken", "")
        if token_address == arb_token_address:
            results["stats"]["token_type"] = "ARB"
            expected_reason = "TLP reward in ARB tokens"
        elif token_address == t_token_address:
            results["stats"]["token_type"] = "T"
            expected_reason = "TLP reward in T tokens"
        else:
            results["valid"] = False
            results["errors"].append(f"Invalid token address: {token_address}")
            return results
        
        # If token_type is specified, ensure it matches
        if token_type and token_type.upper() != results["stats"]["token_type"]:
            results["valid"] = False
            results["errors"].append(f"Expected token type {token_type}, but found {results['stats']['token_type']}")
            return results
        
        # 3. Validate rewards
        rewards = data.get("rewards", {})
        if not rewards:
            results["valid"] = False
            results["errors"].append("No rewards found")
            return results
        
        results["stats"]["total_recipients"] = len(rewards)
        
        for recipient, reward_data in rewards.items():
            # Validate recipient address
            if not validate_ethereum_address(recipient):
                results["valid"] = False
                results["errors"].append(f"Invalid recipient address: {recipient}")
            
            # Validate reward data structure
            if not isinstance(reward_data, dict) or len(reward_data) != 1:
                results["valid"] = False
                results["errors"].append(f"Invalid reward data for {recipient}: {reward_data}")
                continue
            
            # Validate reward reason
            if expected_reason not in reward_data:
                results["valid"] = False
                results["errors"].append(f"Missing expected reason '{expected_reason}' for {recipient}")
                continue
            
            # Validate reward amount
            reward_amount_str = reward_data.get(expected_reason, "")
            if not reward_amount_str or not reward_amount_str.isdigit():
                results["valid"] = False
                results["errors"].append(f"Invalid reward amount for {recipient}: {reward_amount_str}")
                continue
            
            # Convert and track statistics
            reward_amount = Decimal(reward_amount_str)
            results["stats"]["total_amount"] += reward_amount
            
            if results["stats"]["min_amount"] is None or reward_amount < results["stats"]["min_amount"]:
                results["stats"]["min_amount"] = reward_amount
                
            if reward_amount > results["stats"]["max_amount"]:
                results["stats"]["max_amount"] = reward_amount
        
        # Convert to human-readable format (assuming 18 decimals)
        decimals = Decimal('1000000000000000000')
        results["stats"]["total_amount_readable"] = float(results["stats"]["total_amount"] / decimals)
        
        if results["stats"]["min_amount"] is not None:
            results["stats"]["min_amount_readable"] = float(results["stats"]["min_amount"] / decimals)
        
        if results["stats"]["max_amount"] is not None:
            results["stats"]["max_amount_readable"] = float(results["stats"]["max_amount"] / decimals)
        
        # Print validation results
        if results["valid"]:
            print(f"✓ File is valid MERKL format for {results['stats']['token_type']} token")
        else:
            print(f"✗ File validation failed with {len(results['errors'])} errors")
        
        print(f"\nStatistics:")
        print(f"  - Token type: {results['stats']['token_type']}")
        print(f"  - Total recipients: {results['stats']['total_recipients']}")
        print(f"  - Total amount: {results['stats']['total_amount_readable']} {results['stats']['token_type']}")
        print(f"  - Min amount: {results['stats']['min_amount_readable']} {results['stats']['token_type']}")
        print(f"  - Max amount: {results['stats']['max_amount_readable']} {results['stats']['token_type']}")
        
        if results["errors"]:
            print("\nErrors:")
            for i, error in enumerate(results["errors"][:10], 1):
                print(f"  {i}. {error}")
            
            if len(results["errors"]) > 10:
                print(f"  ... and {len(results['errors']) - 10} more errors")
        
        return results
    
    except Exception as e:
        print(f"Error validating MERKL file: {str(e)}")
        return {"valid": False, "errors": [str(e)]}


def validate_merkl_pair(arb_file, t_file):
    """
    Validate both ARB and T MERKL files as a pair.
    
    Parameters:
    - arb_file: Path to the ARB MERKL format JSON file
    - t_file: Path to the T MERKL format JSON file
    
    Returns:
    - Dictionary with paired validation results
    """
    print("\n" + "="*50)
    print("Validating MERKL file pair")
    print("="*50)
    
    # Validate individual files
    arb_results = validate_merkl_file(arb_file, "ARB")
    print("\n" + "-"*50)
    t_results = validate_merkl_file(t_file, "T")
    
    # Check if both files are individually valid
    if not arb_results["valid"] or not t_results["valid"]:
        print("\n✗ Paired validation failed: One or both files are invalid")
        return {
            "valid": False,
            "arb_results": arb_results,
            "t_results": t_results
        }
    
    # Compare recipient lists
    arb_recipients = set(arb_results["rewards"].keys())
    t_recipients = set(t_results["rewards"].keys())
    
    # If we couldn't get the recipients, return early
    if not arb_recipients or not t_recipients:
        print("\n✗ Paired validation failed: Could not extract recipient lists")
        return {
            "valid": False,
            "arb_results": arb_results,
            "t_results": t_results
        }
    
    # Conduct further validations 
    # Check if recipient lists match
    if arb_recipients != t_recipients:
        missing_in_arb = t_recipients - arb_recipients
        missing_in_t = arb_recipients - t_recipients
        
        print("\n✗ Recipient lists do not match between files")
        
        if missing_in_arb:
            print(f"  - {len(missing_in_arb)} recipients missing in ARB file")
            for addr in list(missing_in_arb)[:5]:
                print(f"    - {addr}")
            if len(missing_in_arb) > 5:
                print(f"    - ... and {len(missing_in_arb) - 5} more")
        
        if missing_in_t:
            print(f"  - {len(missing_in_t)} recipients missing in T file")
            for addr in list(missing_in_t)[:5]:
                print(f"    - {addr}")
            if len(missing_in_t) > 5:
                print(f"    - ... and {len(missing_in_t) - 5} more")
                
        return {
            "valid": False,
            "arb_results": arb_results,
            "t_results": t_results,
            "missing_in_arb": missing_in_arb,
            "missing_in_t": missing_in_t
        }
    
    # All validations passed
    print("\n✓ Paired validation passed!")
    print(f"  - ARB file recipients: {arb_results['stats']['total_recipients']}")
    print(f"  - T file recipients: {t_results['stats']['total_recipients']}")
    print(f"  - Total ARB amount: {arb_results['stats']['total_amount_readable']} ARB")
    print(f"  - Total T amount: {t_results['stats']['total_amount_readable']} T")
    
    return {
        "valid": True,
        "arb_results": arb_results,
        "t_results": t_results
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate MERKL format JSON files")
    
    # Define mutually exclusive group to either validate a single file or a pair
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single MERKL format JSON file")
    group.add_argument("--pair", nargs=2, metavar=('ARB_FILE', 'T_FILE'), 
                      help="Paths to ARB and T MERKL format JSON files")
    
    args = parser.parse_args()
    
    if args.file:
        validate_merkl_file(args.file)
    else:
        validate_merkl_pair(args.pair[0], args.pair[1]) 