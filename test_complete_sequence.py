#!/usr/bin/env python3
"""Test complete genomic sequence retrieval"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.gene_server_v2 import GeneToGenomicServer

async def test_complete_sequence():
    print("Testing Complete Genomic Sequence Retrieval...")
    
    server = GeneToGenomicServer()
    
    # Test with TP53 (should be around 19,069 bp)
    print("\n🧬 Testing TP53 complete genomic sequence...")
    
    arguments = {
        "gene_name": "TP53",
        "organism": "human"
    }
    
    try:
        result = await server.gene_to_sequence(arguments)
        
        print("✅ Result received!")
        print("📊 Summary:")
        
        # Extract key information
        lines = result.split('\n')
        for line in lines[:10]:  # First 10 lines
            if any(keyword in line for keyword in ['Gene:', 'Location:', 'Length:', 'Sequence Length:']):
                print(f"  {line}")
        
        # Check if we got FASTA sequence
        fasta_found = False
        sequence_lines = 0
        for line in lines:
            if line.startswith('>'):
                fasta_found = True
                print(f"  FASTA Header: {line[:80]}...")
            elif fasta_found and line.strip() and not line.startswith('🧬') and not line.startswith('📍') and not line.startswith('📏') and not line.startswith('🔬'):
                sequence_lines += 1
        
        print(f"  📈 DNA sequence lines: {sequence_lines}")
        print(f"  📏 Total result length: {len(result):,} characters")
        
        # Verify completeness
        if "19,069" in result and fasta_found and sequence_lines > 100:
            print("🎉 Complete genomic sequence successfully retrieved!")
            return True
        else:
            print("❌ Sequence may be incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    success = await test_complete_sequence()
    print(f"\nComplete Sequence Test: {'PASSED' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)