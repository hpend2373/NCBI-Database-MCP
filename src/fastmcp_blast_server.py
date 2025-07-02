#!/usr/bin/env python3
"""
FastMCP BLAST Server
"""

import subprocess
import tempfile
import os
from pathlib import Path
from fastmcp import FastMCP

# Create the FastMCP app
mcp = FastMCP("Bio BLAST")

@mcp.tool()
def blastn(query: str, database: str, evalue: float = 10.0, max_hits: int = 10) -> str:
    """
    Nucleotide-nucleotide BLAST search
    
    Args:
        query: Query sequence (FASTA format or raw sequence)
        database: Target database name (e.g., 'nt', 'nr')
        evalue: E-value threshold (default: 10.0)
        max_hits: Maximum number of hits to return (default: 10)
    
    Returns:
        BLAST search results in formatted text
    """
    return run_blast("blastn", query, database, evalue, max_hits)

@mcp.tool()
def blastp(query: str, database: str, evalue: float = 10.0, max_hits: int = 10) -> str:
    """
    Protein-protein BLAST search
    
    Args:
        query: Query sequence (FASTA format or raw sequence)
        database: Target database name (e.g., 'nr', 'swissprot')
        evalue: E-value threshold (default: 10.0)
        max_hits: Maximum number of hits to return (default: 10)
    
    Returns:
        BLAST search results in formatted text
    """
    return run_blast("blastp", query, database, evalue, max_hits)

def run_blast(blast_type: str, query: str, database: str, evalue: float, max_hits: int) -> str:
    """Run BLAST search and return formatted results"""
    
    # Create temporary file for query
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        # If query doesn't start with '>', add FASTA header
        if not query.strip().startswith('>'):
            f.write(f">query\n{query}\n")
        else:
            f.write(query)
        query_file = f.name
    
    try:
        # Build BLAST command
        cmd = [
            blast_type,
            "-query", query_file,
            "-db", database,
            "-evalue", str(evalue),
            "-max_target_seqs", str(max_hits),
            "-outfmt", "6 qaccver saccver pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle"
        ]
        
        # Run BLAST
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            return f"❌ BLAST failed: {result.stderr}"
        
        # Format results
        if not result.stdout.strip():
            return "✅ BLAST search completed - No significant hits found"
        
        # Parse and format results
        lines = result.stdout.strip().split('\n')
        formatted_results = f"✅ BLAST {blast_type.upper()} Results\n"
        formatted_results += "="*50 + "\n\n"
        
        for i, line in enumerate(lines[:max_hits], 1):
            fields = line.split('\t')
            if len(fields) >= 13:
                formatted_results += f"Hit {i}:\n"
                formatted_results += f"  Subject: {fields[1]}\n"
                formatted_results += f"  Description: {fields[12]}\n"
                formatted_results += f"  Identity: {fields[2]}%\n"
                formatted_results += f"  E-value: {fields[10]}\n"
                formatted_results += f"  Bit score: {fields[11]}\n"
                formatted_results += f"  Alignment length: {fields[3]}\n\n"
        
        return formatted_results
        
    except subprocess.TimeoutExpired:
        return "❌ BLAST search timed out after 5 minutes"
    except Exception as e:
        return f"❌ Error running BLAST: {str(e)}"
    finally:
        # Clean up temporary file
        try:
            os.unlink(query_file)
        except:
            pass

if __name__ == "__main__":
    mcp.run()