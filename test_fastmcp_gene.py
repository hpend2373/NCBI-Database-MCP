#!/usr/bin/env python3
"""Test the gene functions directly"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.fastmcp_gene_server import search_gene, get_coordinates, fetch_sequence

def test_tp53():
    print("Testing TP53 workflow...")
    
    # Step 1: Search gene
    gene_id = search_gene("TP53", "human")
    if gene_id:
        print(f"✓ Found gene ID: {gene_id}")
    else:
        print("✗ Gene ID not found")
        return False
    
    # Step 2: Get coordinates
    coords = get_coordinates(gene_id)
    if coords:
        print(f"✓ Found coordinates: {coords}")
    else:
        print("✗ Coordinates not found")
        return False
    
    # Step 3: Get sequence (small portion)
    sequence = fetch_sequence(coords["chr"], coords["start"], coords["start"] + 1000)
    if sequence:
        print(f"✓ Got sequence (first 200 chars): {sequence[:200]}...")
        return True
    else:
        print("✗ Sequence not found")
        return False

if __name__ == "__main__":
    success = test_tp53()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)