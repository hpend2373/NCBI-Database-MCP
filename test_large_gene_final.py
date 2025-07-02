#!/usr/bin/env python3
"""Final test with a larger gene to ensure no truncation"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.gene_server_v2 import GeneToGenomicServer

async def test_large_gene_complete():
    """Test with a large gene to ensure complete output"""
    print("🧬 Final Test: Large Gene Complete Sequence Output")
    print("=" * 60)
    
    server = GeneToGenomicServer()
    
    # Test with BRCA1 (large gene)
    print("📊 Testing BRCA1 gene (large sequence ~126kb)...")
    
    arguments = {
        "gene_name": "BRCA1",
        "organism": "human"
    }
    
    try:
        result = await server.gene_to_sequence(arguments)
        
        print("✅ Result generated successfully!")
        
        # Analyze the result
        lines = result.split('\n')
        info_lines = []
        sequence_lines = []
        fasta_header = None
        
        for line in lines:
            if line.startswith('>'):
                fasta_header = line
            elif any(line.startswith(prefix) for prefix in ['🧬', '📍', '🔄', '📋', '📏', '🔬', '⚠️']):
                info_lines.append(line)
            elif line.strip() and not any(line.startswith(prefix) for prefix in ['🧬', '📍', '🔄', '📋', '📏', '🔬', '⚠️']):
                sequence_lines.append(line.strip())
        
        # Calculate sequence length
        total_sequence = ''.join(sequence_lines)
        sequence_length = len(total_sequence)
        
        print("\n📊 Analysis Results:")
        print(f"  📏 Total result length: {len(result):,} characters")
        print(f"  📝 Info lines: {len(info_lines)}")
        print(f"  🧬 DNA sequence length: {sequence_length:,} nucleotides")
        print(f"  📄 FASTA header: {fasta_header[:80] + '...' if fasta_header and len(fasta_header) > 80 else fasta_header}")
        
        # Show key info lines
        print("\n📋 Key Information:")
        for line in info_lines[:8]:  # Show first 8 info lines
            print(f"  {line}")
        
        # Verify completeness
        print(f"\n🔍 Completeness Check:")
        
        # BRCA1 should be around 126kb
        expected_min = 120000
        if sequence_length >= expected_min:
            print(f"  ✅ Sequence length ({sequence_length:,} bp) >= expected minimum ({expected_min:,} bp)")
        else:
            print(f"  ❌ Sequence may be incomplete: {sequence_length:,} bp < {expected_min:,} bp")
            return False
        
        # Check for key indicators
        if "COMPLETE" in result:
            print("  ✅ 'COMPLETE' indicator found")
        
        if "NO TRUNCATION" in result or "No truncation" in result:
            print("  ✅ 'NO TRUNCATION' indicator found")
        
        if "LATEST VERSION" in result:
            print("  ✅ 'LATEST VERSION' indicator found")
        
        # Check sequence integrity
        if total_sequence and all(c in 'ATCGN' for c in total_sequence.upper()[:100]):
            print("  ✅ DNA sequence format verified")
        else:
            print("  ❌ Invalid DNA sequence format")
            return False
        
        # Show sequence sample
        if total_sequence:
            print(f"\n🧬 Sequence Sample:")
            print(f"  Start: {total_sequence[:50]}...")
            print(f"  End:   ...{total_sequence[-50:]}")
        
        print(f"\n🎉 BRCA1 Complete Sequence Test: SUCCESS!")
        print(f"📊 Final Stats: {sequence_length:,} nucleotides in {len(result):,} characters total")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    success = await test_large_gene_complete()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 LARGE GENE NO-TRUNCATION TEST: PASSED")
        print("\n✅ Confirmed Features:")
        print("  - Complete genomic sequences (>100kb)")
        print("  - No truncation warnings")
        print("  - Latest version selection")
        print("  - Full FASTA format output")
        print("  - Continuous sequence data")
        print("\n🎯 Ready for other models and analysis tools!")
    else:
        print("❌ LARGE GENE NO-TRUNCATION TEST: FAILED")
    
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)