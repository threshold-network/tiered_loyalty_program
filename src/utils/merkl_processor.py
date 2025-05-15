import argparse
import os
import sys
import os.path

# Add the parent directory to sys.path to enable relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.rewards_validator import validate_rewards_file
from utils.merkl_converter import convert_to_merkl_format


def process_rewards_for_merkl(input_file, output_dir):
    """
    Process rewards file for MERKL:
    1. Validate the rewards file
    2. Convert to MERKL format if validation passes
    """
    print("=" * 50)
    print(f"Processing rewards file: {input_file}")
    print("=" * 50)
    
    # Step 1: Validate the rewards file
    print("\nStep 1: Validating rewards file...")
    validation_results = validate_rewards_file(input_file)
    
    if not validation_results:
        print("\nValidation failed. Cannot proceed with conversion.")
        return False
    
    # Check if critical validations passed
    critical_validations = [
        validation_results["weighted_liquidity_match"]["result"],
        validation_results["arb_tokens_sum"]["result"],
        validation_results["t_usd_percentage"]["result"]
    ]
    
    if not all(critical_validations):
        print("\nCritical validation checks failed. Please review the validation results above.")
        proceed = input("\nDo you want to proceed with conversion anyway? (y/n): ").strip().lower()
        
        if proceed != 'y':
            print("Conversion cancelled.")
            return False
    
    # Step 2: Convert to MERKL format
    print("\nStep 2: Converting to MERKL format...")
    conversion_success = convert_to_merkl_format(input_file, output_dir)
    
    if conversion_success:
        print("\nConversion successful!")
        print(f"MERKL format files saved to: {output_dir}")
        
        # Remind about MERKL fee
        print("\nIMPORTANT NOTE ABOUT MERKL FEE:")
        print("Merkl applies a 0.5% fee to airdrop campaigns.")
        print("This fee is added on top of the total airdropped amount.")
        print("The frontend will automatically calculate this for you when uploading to MERKL.")
        
        return True
    else:
        print("\nConversion failed.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process rewards file for MERKL")
    parser.add_argument("input_file", help="Path to the rewards JSON file")
    parser.add_argument("--output-dir", default="data/merkl", help="Directory to save MERKL format files")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    process_rewards_for_merkl(args.input_file, args.output_dir) 