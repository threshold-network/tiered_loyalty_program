# MERKL Airdrop Processing Scripts

This directory contains scripts for processing rewards data for the MERKL airdrop platform.

## Scripts Overview

1. `merkl_converter.py` - Converts the rewards JSON to MERKL format for both ARB and T tokens
2. `rewards_validator.py` - Validates the rewards JSON according to specified requirements
3. `merkl_processor.py` - Main script that runs both validation and conversion
4. `merkl_validator.py` - Validates MERKL format JSON files for submission to the MERKL platform

## Requirements

- Python 3.7+
- Required modules: `json`, `argparse`, `decimal`, `os`, `sys`, `re`

## Usage

### 1. Validating Rewards File Only

```bash
python rewards_validator.py /path/to/rewards.json
```

This will validate the rewards file according to these requirements:
- Check if sum of weighted_avg_liquidity equals total_weighted_liquidity
- Sum all reward fields
- Check if ARB token sum is 50,000
- Check if T token USD value is 25% of ARB token USD value
- Calculate relative token prices

### 2. Converting Rewards File to MERKL Format Only

```bash
python merkl_converter.py /path/to/rewards.json --output-dir data/merkl
```

This will convert the rewards JSON to two MERKL format files:
- ARB token distribution file: `{filename}_merkl_arb.json`
- T token distribution file: `{filename}_merkl_t.json`

### 3. Complete Processing (Validate and Convert)

```bash
python merkl_processor.py /path/to/rewards.json --output-dir data/merkl
```

This will first validate the rewards file, and if validation passes (or user chooses to proceed), it will convert the file to MERKL format.

### 4. Validating MERKL Format Files

```bash
# Validate a single MERKL file
python merkl_validator.py --file /path/to/merkl_file.json

# Validate a pair of ARB and T token MERKL files
python merkl_validator.py --pair /path/to/arb_file.json /path/to/t_file.json
```

This will validate that the MERKL format files are correctly formatted and provide statistics about the distributions:
- Validates token addresses
- Checks recipient addresses
- Validates rewards format and amounts
- When validating a pair, ensures both files have the same set of recipients

## MERKL Format

The MERKL format follows this structure for both ARB and T tokens:

```json
{
  "rewardToken": "0xTOKEN_ADDRESS",
  "rewards": {
    "0xRECIPIENT_ADDRESS": {
      "TLP reward in ARB tokens": "TOKEN_AMOUNT_WITH_DECIMALS"
    },
    ...
  }
}
```

## Token Addresses

- ARB on Ethereum Mainnet: `0xb50721bcf8d664c30412cfbc6cf7a15145234ad1`
- T on Ethereum Mainnet: `0xcdf7028ceab81fa0c6971208e83fa7872994bee5`

## Important Note About MERKL Fee

Merkl applies a 0.5% fee to airdrop campaigns. This fee is added on top of the total airdropped amount, ensuring recipients receive the full intended distribution.

The MERKL web interface will automatically calculate this fee when you upload the files. 

```bash
python src/utils/merkl_processor.py data/rewards/rewards_20250514_165141.json --output-dir data/merkl
``` 