#!/usr/bin/env python3
"""
FastMCP Gene-to-Genomic Server
Simple and reliable implementation using FastMCP
"""

import asyncio
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import logging
import sys
from typing import Optional

import fastmcp

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# NCBI Configuration
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = os.getenv('NCBI_API_KEY')  # Set via environment variable

# Create FastMCP server
mcp = fastmcp.FastMCP("Gene-to-Genomic")

@mcp.tool()
def gene_to_sequence(gene_name: str, organism: str = "human") -> str:
    """
    Convert gene name to genomic DNA sequence using NCBI E-utilities.
    
    Args:
        gene_name: Gene symbol (e.g., TP53, BRCA1)
        organism: Organism name (default: human)
    
    Returns:
        Genomic DNA sequence in FASTA format with location information
    """
    try:
        logger.info(f"Processing gene: {gene_name} ({organism})")
        
        # Step 1: Search for gene ID
        gene_id = search_gene(gene_name, organism)
        if not gene_id:
            return f"❌ Gene '{gene_name}' not found in {organism}"
        
        logger.info(f"Found gene ID: {gene_id}")
        
        # Step 2: Get genomic coordinates
        coords = get_coordinates(gene_id)
        if not coords:
            return f"❌ Genomic coordinates not found for {gene_name}"
        
        logger.info(f"Found coordinates: {coords}")
        
        # Step 3: Fetch sequence
        sequence = fetch_sequence(coords["chr"], coords["start"], coords["end"])
        if not sequence:
            return f"❌ Sequence not available for {gene_name}"
        
        # Format result
        result = f"🧬 Gene: {gene_name} ({organism})\n"
        result += f"📍 Location: {coords['chr']}:{coords['start']:,}-{coords['end']:,}\n"
        result += f"📏 Length: {coords['end'] - coords['start']:,} bp\n\n"
        result += sequence
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing {gene_name}: {e}")
        return f"❌ Error: {str(e)}"

def search_gene(gene_name: str, organism: str) -> Optional[str]:
    """Search for gene ID in NCBI Gene database"""
    try:
        query = f"{gene_name}[GENE] AND {organism}[ORGN]"
        params = {
            "db": "gene",
            "term": query,
            "retmode": "xml",
            "retmax": "1",
            "api_key": NCBI_API_KEY
        }
        
        url = f"{NCBI_BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        response = http_request(url)
        
        root = ET.fromstring(response)
        id_list = root.find("IdList")
        if id_list is not None and len(id_list) > 0:
            return id_list.find("Id").text
        return None
        
    except Exception as e:
        logger.error(f"Gene search error: {e}")
        return None

def get_coordinates(gene_id: str) -> Optional[dict]:
    """Get genomic coordinates for gene"""
    try:
        params = {
            "db": "gene",
            "id": gene_id,
            "retmode": "xml",
            "api_key": NCBI_API_KEY
        }
        
        url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
        response = http_request(url)
        
        root = ET.fromstring(response)
        doc_sum = root.find("DocumentSummary")
        if doc_sum is None:
            doc_sum = root.find(".//DocumentSummary")
        
        if doc_sum is not None:
            # Look for GenomicInfo/GenomicInfoType
            genomic_info = doc_sum.find("GenomicInfo")
            if genomic_info is not None:
                genomic_info_type = genomic_info.find("GenomicInfoType")
                if genomic_info_type is not None:
                    coords = {}
                    
                    chr_acc = genomic_info_type.find("ChrAccVer")
                    chr_start = genomic_info_type.find("ChrStart")
                    chr_stop = genomic_info_type.find("ChrStop")
                    
                    if chr_acc is not None and chr_start is not None and chr_stop is not None:
                        coords["chr"] = chr_acc.text
                        start_pos = int(chr_start.text)
                        stop_pos = int(chr_stop.text)
                        
                        # NCBI sometimes has start > stop (reverse strand)
                        coords["start"] = min(start_pos, stop_pos)
                        coords["end"] = max(start_pos, stop_pos)
                        
                        return coords
        
        return None
        
    except Exception as e:
        logger.error(f"Coordinates error: {e}")
        return None

def fetch_sequence(chromosome: str, start: int, end: int) -> Optional[str]:
    """Fetch genomic sequence from NCBI"""
    try:
        params = {
            "db": "nuccore",
            "id": chromosome,
            "seq_start": str(start),
            "seq_stop": str(end),
            "rettype": "fasta",
            "retmode": "text",
            "api_key": NCBI_API_KEY
        }
        
        url = f"{NCBI_BASE_URL}/efetch.fcgi?{urllib.parse.urlencode(params)}"
        response = http_request(url)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Sequence fetch error: {e}")
        return None

def http_request(url: str) -> str:
    """Make HTTP request"""
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode('utf-8')

if __name__ == "__main__":
    print("Starting FastMCP Gene-to-Genomic Server...", file=sys.stderr)
    mcp.run()