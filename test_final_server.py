#!/usr/bin/env python3
"""Test the final gene server functionality"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.gene_server_final import gene_to_sequence, search_gene_info

async def test_gene_functions():
    print("Testing Gene Server Functions...")
    
    # Test 1: Search gene info
    print("\n1. Testing search_gene_info with TP53...")
    try:
        result1 = await search_gene_info({"gene_name": "TP53", "organism": "human"})
        print("✓ search_gene_info result:")
        print(result1)
    except Exception as e:
        print(f"✗ search_gene_info failed: {e}")
        return False
    
    # Test 2: Gene to sequence (small portion)
    print("\n2. Testing gene_to_sequence with TP53 (first 1000 bp)...")
    try:
        # We'll modify the fetch to only get first 1000 bp for testing
        result2 = await gene_to_sequence({"gene_name": "TP53", "organism": "human"})
        print("✓ gene_to_sequence result (first 300 chars):")
        print(result2[:300] + "..." if len(result2) > 300 else result2)
    except Exception as e:
        print(f"✗ gene_to_sequence failed: {e}")
        return False
    
    return True

async def main():
    success = await test_gene_functions()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)