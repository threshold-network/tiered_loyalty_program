import json
import os
import argparse
from decimal import Decimal


def convert_to_merkl_format(input_file, output_dir):
    """
    Convert the rewards JSON file to MERKL format for both ARB and T tokens.
    Creates two separate JSON files for ARB and T tokens distribution.
    """
    try:
        print(f"Reading rewards file: {input_file}")
        with open(input_file, 'r') as f:
            rewards_data = json.load(f)
        
        if 'rewards' not in rewards_data:
            raise ValueError("Invalid rewards file format: 'rewards' key not found")
        
        # ARB token address on Ethereum Mainnet
        arb_token_address = "0x912ce59144191c1204e64559fe8253a0e49e6548"  # Replace with your new ARB token address
        # T token address on Ethereum Mainnet
        t_token_address = "0xcdf7028ceab81fa0c6971208e83fa7872994bee5"
        
        # Initialize MERKL format dictionaries
        arb_merkl = {
            "rewardToken": arb_token_address,
            "rewards": {}
        }
        
        t_merkl = {
            "rewardToken": t_token_address,
            "rewards": {}
        }
        
        # Process each reward entry in the list
        for reward_data in rewards_data["rewards"]:
            # Get provider address (recipient)
            provider = reward_data.get("provider")
            if not provider:
                print(f"Warning: Provider address not found, skipping")
                continue
            
            # Get ARB and T token amounts
            arb_amount = reward_data.get("estimated_reward_in_arb_tokens")
            t_amount = reward_data.get("estimated_reward_in_t_tokens")
            
            # Skip if amounts are missing
            if arb_amount is None or t_amount is None:
                print(f"Warning: Token amounts missing for {provider}, skipping")
                continue
            
            # Convert to string with full precision (MERKL format requires string amounts)
            # Convert to integer string with all decimals (assuming 18 decimals)
            arb_amount_str = str(int(Decimal(str(arb_amount)) * Decimal('1000000000000000000')))
            t_amount_str = str(int(Decimal(str(t_amount)) * Decimal('1000000000000000000')))
            
            # Add to ARB MERKL format if amount > 0
            if Decimal(arb_amount) > 0:
                if provider not in arb_merkl["rewards"]:
                    arb_merkl["rewards"][provider] = {}
                arb_merkl["rewards"][provider]["TLP reward in ARB tokens"] = arb_amount_str
            
            # Add to T MERKL format if amount > 0
            if Decimal(t_amount) > 0:
                if provider not in t_merkl["rewards"]:
                    t_merkl["rewards"][provider] = {}
                t_merkl["rewards"][provider]["TLP reward in T tokens"] = t_amount_str
        
        # Generate output filenames based on input filename
        base_filename = os.path.basename(input_file)
        filename_without_ext = os.path.splitext(base_filename)[0]
        
        arb_output_file = os.path.join(output_dir, f"{filename_without_ext}_merkl_arb.json")
        t_output_file = os.path.join(output_dir, f"{filename_without_ext}_merkl_t.json")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save ARB MERKL file
        with open(arb_output_file, 'w') as f:
            json.dump(arb_merkl, f, indent=2)
        print(f"ARB token MERKL format saved to: {arb_output_file}")
        
        # Save T MERKL file
        with open(t_output_file, 'w') as f:
            json.dump(t_merkl, f, indent=2)
        print(f"T token MERKL format saved to: {t_output_file}")
        
        return True
    
    except Exception as e:
        print(f"Error converting to MERKL format: {str(e)}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert rewards JSON to MERKL format")
    parser.add_argument("input_file", help="Path to the rewards JSON file")
    parser.add_argument("--output-dir", default="data/merkl", help="Directory to save MERKL format files")
    
    args = parser.parse_args()
    
    convert_to_merkl_format(args.input_file, args.output_dir) 