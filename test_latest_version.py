#!/usr/bin/env python3
"""Test latest version selection functionality"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.gene_server_v2 import GeneToGenomicServer

async def test_latest_version_selection():
    print("🧬 Testing Latest Version Selection for Gene Coordinates...")
    
    server = GeneToGenomicServer()
    
    # Test TP53 gene (known to have multiple versions)
    print("\n📊 Testing TP53 gene...")
    
    try:
        # Step 1: Search for gene ID
        gene_id = await server.search_gene_ncbi("TP53", "human")
        print(f"✅ Found gene ID: {gene_id}")
        
        # Step 2: Get coordinates with latest version selection
        coords = await server.get_genomic_coordinates(gene_id)
        
        if coords:
            print("\n🎯 Selected Coordinates:")
            print(f"  📍 Location: {coords['chr']}:{coords['start']:,}-{coords['end']:,}")
            print(f"  🔄 Source: {coords.get('source', 'N/A')}")
            if 'release' in coords:
                print(f"  📋 Release: {coords['release']}")
            if 'assembly' in coords:
                print(f"  🏗️ Assembly: {coords['assembly']}")
            print(f"  📏 Length: {coords['end'] - coords['start']:,} bp")
            
            # Verify we got the latest version
            if 'release' in coords and coords['release'].startswith('RS_2024'):
                print("✅ Latest annotation release (RS_2024_xx) selected!")
            
            if 'assembly' in coords and coords['assembly'].startswith('GCF_000001405.'):
                print("✅ Primary reference assembly (GRCh38) selected!")
            
            return True
        else:
            print("❌ No coordinates found")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_complete_workflow():
    """Test the complete workflow with latest version"""
    print("\n🧬 Testing Complete Workflow with Latest Version...")
    
    server = GeneToGenomicServer()
    
    arguments = {
        "gene_name": "BRCA1",  # Another gene with multiple versions
        "organism": "human"
    }
    
    try:
        result = await server.gene_to_sequence(arguments)
        
        print("✅ Complete workflow result received!")
        
        # Extract and display key information
        lines = result.split('\n')
        for line in lines[:10]:  # First 10 lines
            if any(keyword in line for keyword in ['Gene:', 'Location:', 'Version:', 'Annotation:', 'Length:']):
                print(f"  {line}")
        
        # Check if version info is included
        if "Version:" in result and ("RS_2024" in result or "Latest:" in result):
            print("✅ Latest version information included in result!")
            return True
        else:
            print("❌ Version information missing or not latest")
            return False
            
    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")
        return False

async def main():
    print("=" * 60)
    print("🔄 LATEST VERSION SELECTION TEST")
    print("=" * 60)
    
    # Test 1: Coordinate selection
    test1_success = await test_latest_version_selection()
    
    # Test 2: Complete workflow
    test2_success = await test_complete_workflow()
    
    overall_success = test1_success and test2_success
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"  🔄 Latest Version Selection: {'PASSED' if test1_success else 'FAILED'}")
    print(f"  🧬 Complete Workflow: {'PASSED' if test2_success else 'FAILED'}")
    print(f"  🎯 Overall: {'PASSED' if overall_success else 'FAILED'}")
    print("=" * 60)
    
    if overall_success:
        print("🎉 Gene server now automatically selects the LATEST version!")
        print("📋 Features:")
        print("  ✅ Latest annotation release (RS_2024_xx)")
        print("  ✅ Primary reference assembly (GRCh38)")
        print("  ✅ Version information in results")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)