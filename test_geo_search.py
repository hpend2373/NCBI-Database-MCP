#!/usr/bin/env python3
"""
Simple test script for GEO dataset search functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from gene_to_genomic_server import GeneToGenomicServer

async def test_geo_search():
    """Test GEO dataset search functionality"""
    print("🧪 Testing GEO Dataset Search Functionality\n")
    
    server = GeneToGenomicServer()
    
    test_cases = [
        {
            "disease": "diabetes",
            "organism": "Homo sapiens",
            "max_results": 5
        },
        {
            "disease": "cancer",
            "organism": "Mus musculus",
            "max_results": 3
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case}")
        print("-" * 50)
        
        try:
            result = await server._search_geo_datasets(**test_case)
            print(result)
            print("\n" + "="*80 + "\n")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    print("Note: Set NCBI_API_KEY environment variable for better performance")
    print("Without API key: 3 requests/second limit")
    print("With API key: 10 requests/second limit\n")
    
    asyncio.run(test_geo_search())