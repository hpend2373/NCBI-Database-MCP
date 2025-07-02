#!/usr/bin/env python3
"""
Test the fixed OSDR organism search functionality
"""
import asyncio
import httpx
import sys
import os

# Add the OSDR server path to sys.path
sys.path.append('/Users/minyeop/alphagenome/bio-mcp-blast/osdr_mcp_server/osdr_example/osdr_mcp')

from main_simple import osdr_find_by_organism

async def test_organism_search():
    """Test the fixed organism search function"""
    print("=== Testing Fixed OSDR Organism Search ===\n")
    
    # Test cases
    test_organisms = ["human", "homo sapiens", "mouse", "drosophila"]
    
    for organism in test_organisms:
        print(f"Testing search for '{organism}':")
        try:
            results = await osdr_find_by_organism(organism)
            print(f"  Found {len(results)} matching datasets")
            
            # Show first 5 results
            for i, result in enumerate(results[:5]):
                print(f"  {i+1}. {result['dataset_id']}: {result['organism']}")
                print(f"     Title: {result['study_title'][:60]}...")
            
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more results")
                
        except Exception as e:
            print(f"  Error: {e}")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_organism_search())