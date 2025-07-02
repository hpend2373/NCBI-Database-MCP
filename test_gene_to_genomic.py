#!/usr/bin/env python3
"""
Test script for Gene-to-Genomic-Sequence MCP Server
Tests the workflow: Gene Name -> Gene ID -> Genomic Coordinates -> DNA Sequence
"""

import asyncio
import json
import sys
from src.gene_to_genomic_server import GeneToGenomicServer, ServerSettings


async def test_tp53_workflow():
    """Test the complete workflow with TP53 gene"""
    print("=== Testing TP53 Gene-to-Genomic Sequence Workflow ===")
    
    server = GeneToGenomicServer()
    
    # Test 1: Search gene info
    print("\n1. Searching TP53 gene information...")
    gene_info_result = await server._search_gene_info({
        "gene_name": "TP53",
        "organism": "human"
    })
    
    if gene_info_result:
        print("✓ Gene search successful")
        print(gene_info_result[0].text[:200] + "..." if len(gene_info_result[0].text) > 200 else gene_info_result[0].text)
    else:
        print("✗ Gene search failed")
        return False
    
    # Test 2: Complete gene-to-genomic workflow
    print("\n2. Running complete gene-to-genomic sequence workflow...")
    sequence_result = await server._gene_to_genomic_sequence({
        "gene_name": "TP53",
        "organism": "human",
        "sequence_type": "genomic",
        "output_format": "fasta"
    })
    
    if sequence_result:
        print("✓ Complete workflow successful")
        result_text = sequence_result[0].text
        print(f"Result length: {len(result_text)} characters")
        print("First 500 characters:")
        print(result_text[:500])
        
        # Check if we got FASTA format
        if result_text.find(">") != -1:
            print("✓ FASTA format detected")
        else:
            print("? No FASTA header found")
            
    else:
        print("✗ Complete workflow failed")
        return False
    
    return True


async def test_brca1_workflow():
    """Test with BRCA1 gene"""
    print("\n=== Testing BRCA1 Gene Workflow ===")
    
    server = GeneToGenomicServer()
    
    sequence_result = await server._gene_to_genomic_sequence({
        "gene_name": "BRCA1",
        "organism": "human",
        "sequence_type": "genomic",
        "output_format": "fasta"
    })
    
    if sequence_result:
        print("✓ BRCA1 workflow successful")
        result_text = sequence_result[0].text
        print(f"Result length: {len(result_text)} characters")
        print("First 300 characters:")
        print(result_text[:300])
        return True
    else:
        print("✗ BRCA1 workflow failed")
        return False


async def test_direct_sequence_fetch():
    """Test direct genomic sequence fetching"""
    print("\n=== Testing Direct Genomic Sequence Fetch ===")
    
    server = GeneToGenomicServer()
    
    # Use known coordinates for TP53 gene
    sequence_result = await server._get_genomic_sequence({
        "chromosome": "NC_000017.11",
        "start": 7661779,
        "end": 7687550,
        "output_format": "fasta"
    })
    
    if sequence_result:
        print("✓ Direct sequence fetch successful")
        result_text = sequence_result[0].text
        print(f"Result length: {len(result_text)} characters")
        print("First 300 characters:")
        print(result_text[:300])
        return True
    else:
        print("✗ Direct sequence fetch failed")
        return False


async def test_error_handling():
    """Test error handling with invalid inputs"""
    print("\n=== Testing Error Handling ===")
    
    server = GeneToGenomicServer()
    
    # Test with non-existent gene
    print("\n1. Testing with non-existent gene...")
    try:
        result = await server._gene_to_genomic_sequence({
            "gene_name": "NONEXISTENTGENE12345",
            "organism": "human"
        })
        
        if "not found" in result[0].text.lower():
            print("✓ Properly handled non-existent gene")
        else:
            print("? Unexpected result for non-existent gene")
            print(result[0].text[:200])
            
    except Exception as e:
        print(f"✗ Error handling failed: {e}")
        return False
    
    # Test with invalid organism
    print("\n2. Testing with invalid organism...")
    try:
        result = await server._gene_to_genomic_sequence({
            "gene_name": "TP53",
            "organism": "invalidorganism12345"
        })
        
        if "not found" in result[0].text.lower():
            print("✓ Properly handled invalid organism")
        else:
            print("? Unexpected result for invalid organism")
            print(result[0].text[:200])
            
    except Exception as e:
        print(f"✗ Error handling failed: {e}")
        return False
    
    return True


async def main():
    """Run all tests"""
    print("Starting Gene-to-Genomic MCP Server Tests")
    print("=========================================")
    
    tests = [
        ("TP53 Workflow", test_tp53_workflow),
        ("BRCA1 Workflow", test_brca1_workflow),
        ("Direct Sequence Fetch", test_direct_sequence_fetch),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"\n{test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"\n{test_name}: FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)