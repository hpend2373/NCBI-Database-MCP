#!/usr/bin/env python3
"""
Final Gene-to-Genomic MCP Server
Based on proven working_blast_server.py pattern
"""

import asyncio
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import sys
import logging
from typing import Any, Sequence, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use exact same MCP imports as working server
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    InitializeRequestParams,
    InitializeResult,
    ServerCapabilities,
    Implementation,
)

# NCBI Configuration
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"

# Create server with exact same pattern
server = Server("gene-to-genomic")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available gene tools"""
    return [
        Tool(
            name="gene_to_sequence",
            description="Convert gene name to genomic DNA sequence using NCBI E-utilities",
            inputSchema={
                "type": "object",
                "properties": {
                    "gene_name": {
                        "type": "string",
                        "description": "Gene symbol (e.g., TP53, BRCA1)"
                    },
                    "organism": {
                        "type": "string",
                        "description": "Organism name (default: human)",
                        "default": "human"
                    }
                },
                "required": ["gene_name"]
            }
        ),
        Tool(
            name="search_gene_info",
            description="Search for gene information and location",
            inputSchema={
                "type": "object",
                "properties": {
                    "gene_name": {
                        "type": "string",
                        "description": "Gene symbol to search"
                    },
                    "organism": {
                        "type": "string",
                        "description": "Organism name (default: human)",
                        "default": "human"
                    }
                },
                "required": ["gene_name"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls"""
    try:
        if name == "gene_to_sequence":
            return [TextContent(text=await gene_to_sequence(arguments))]
        elif name == "search_gene_info":
            return [TextContent(text=await search_gene_info(arguments))]
        else:
            return [TextContent(text=f"❌ Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [TextContent(text=f"❌ Error: {str(e)}")]

async def gene_to_sequence(arguments: dict) -> str:
    """Convert gene name to genomic sequence"""
    gene_name = arguments["gene_name"]
    organism = arguments.get("organism", "human")
    
    logger.info(f"Processing gene: {gene_name} ({organism})")
    
    # Step 1: Search for gene ID
    gene_id = await search_gene_ncbi(gene_name, organism)
    if not gene_id:
        return f"❌ Gene '{gene_name}' not found in {organism}"
    
    logger.info(f"Found gene ID: {gene_id}")
    
    # Step 2: Get genomic coordinates
    coords = await get_genomic_coordinates(gene_id)
    if not coords:
        return f"❌ Genomic coordinates not found for {gene_name}"
    
    logger.info(f"Found coordinates: {coords}")
    
    # Step 3: Fetch sequence
    sequence = await fetch_genomic_sequence(coords["chr"], coords["start"], coords["end"])
    if not sequence:
        return f"❌ Sequence not available for {gene_name}"
    
    # Format result
    result = f"🧬 Gene: {gene_name} ({organism})\n"
    result += f"📍 Location: {coords['chr']}:{coords['start']:,}-{coords['end']:,}\n"
    result += f"📏 Length: {coords['end'] - coords['start']:,} bp\n\n"
    result += sequence
    
    return result

async def search_gene_info(arguments: dict) -> str:
    """Search for gene information"""
    gene_name = arguments["gene_name"]
    organism = arguments.get("organism", "human")
    
    # Step 1: Search for gene ID
    gene_id = await search_gene_ncbi(gene_name, organism)
    if not gene_id:
        return f"❌ Gene '{gene_name}' not found in {organism}"
    
    # Step 2: Get genomic coordinates
    coords = await get_genomic_coordinates(gene_id)
    if not coords:
        return f"❌ Genomic coordinates not found for {gene_name}"
    
    # Format result
    result = f"🧬 Gene Information: {gene_name} ({organism})\n"
    result += f"🔢 Gene ID: {gene_id}\n"
    result += f"📍 Location: {coords['chr']}:{coords['start']:,}-{coords['end']:,}\n"
    result += f"📏 Length: {coords['end'] - coords['start']:,} bp\n"
    
    return result

async def search_gene_ncbi(gene_name: str, organism: str) -> Optional[str]:
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
        response = await make_http_request(url)
        
        root = ET.fromstring(response)
        id_list = root.find("IdList")
        if id_list is not None and len(id_list) > 0:
            return id_list.find("Id").text
        return None
        
    except Exception as e:
        logger.error(f"Gene search error: {e}")
        return None

async def get_genomic_coordinates(gene_id: str) -> Optional[dict]:
    """Get genomic coordinates for gene"""
    try:
        params = {
            "db": "gene",
            "id": gene_id,
            "retmode": "xml",
            "api_key": NCBI_API_KEY
        }
        
        url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
        response = await make_http_request(url)
        
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

async def fetch_genomic_sequence(chromosome: str, start: int, end: int) -> Optional[str]:
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
        response = await make_http_request(url)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Sequence fetch error: {e}")
        return None

async def make_http_request(url: str) -> str:
    """Make HTTP request using asyncio executor"""
    loop = asyncio.get_event_loop()
    
    def make_request():
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode('utf-8')
    
    return await loop.run_in_executor(None, make_request)

async def main():
    """Main server function - exact same pattern as working server"""
    print("Starting Gene-to-Genomic MCP Server...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        print("Server initialized, waiting for connections...", file=sys.stderr)
        
        # Pass empty initialization options - exact same as working server
        init_options = {}
        await server.run(
            read_stream, 
            write_stream, 
            init_options
        )

if __name__ == "__main__":
    asyncio.run(main())