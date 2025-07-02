#!/usr/bin/env python3
"""
Working Gene-to-Genomic MCP Server
Based on working BLAST server pattern
"""

import asyncio
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import logging
from typing import Any, Sequence

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use latest MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)

# NCBI Configuration
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"

# Create server
server = Server("gene-to-genomic")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available gene tools"""
    return [
        Tool(
            name="gene_to_sequence",
            description="Convert gene name to genomic DNA sequence using NCBI",
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
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls"""
    if name == "gene_to_sequence":
        return await gene_to_sequence(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def gene_to_sequence(args: dict) -> Sequence[TextContent]:
    """Convert gene name to genomic sequence"""
    try:
        gene_name = args["gene_name"]
        organism = args.get("organism", "human")
        
        logger.info(f"Processing gene: {gene_name} ({organism})")
        
        # Step 1: Find gene ID
        gene_id = await search_gene(gene_name, organism)
        if not gene_id:
            return [TextContent(type="text", text=f"❌ Gene '{gene_name}' not found in {organism}")]
        
        logger.info(f"Found gene ID: {gene_id}")
        
        # Step 2: Get genomic coordinates
        coords = await get_coordinates(gene_id)
        if not coords:
            return [TextContent(type="text", text=f"❌ Genomic coordinates not found for {gene_name}")]
        
        logger.info(f"Found coordinates: {coords}")
        
        # Step 3: Get sequence
        sequence = await fetch_sequence(coords["chr"], coords["start"], coords["end"])
        if not sequence:
            return [TextContent(type="text", text=f"❌ Sequence not available for {gene_name}")]
        
        # Format result
        result = f"🧬 Gene: {gene_name} ({organism})\n"
        result += f"📍 Location: {coords['chr']}:{coords['start']:,}-{coords['end']:,}\n"
        result += f"📏 Length: {coords['end'] - coords['start']:,} bp\n\n"
        result += sequence
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Error processing {gene_name}: {e}")
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

async def search_gene(gene_name: str, organism: str) -> str:
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
        response = await http_request(url)
        
        root = ET.fromstring(response)
        id_list = root.find("IdList")
        if id_list is not None and len(id_list) > 0:
            return id_list.find("Id").text
        return None
        
    except Exception as e:
        logger.error(f"Gene search error: {e}")
        return None

async def get_coordinates(gene_id: str) -> dict:
    """Get genomic coordinates for gene"""
    try:
        params = {
            "db": "gene",
            "id": gene_id,
            "retmode": "xml",
            "api_key": NCBI_API_KEY
        }
        
        url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
        response = await http_request(url)
        
        root = ET.fromstring(response)
        doc_sum = root.find("DocSum")
        
        if doc_sum is not None:
            for item in doc_sum.findall("Item"):
                if item.get("Name") == "GenomicInfo":
                    coords = {}
                    for sub_item in item.findall("Item"):
                        name = sub_item.get("Name")
                        if name == "ChrAccVer":
                            coords["chr"] = sub_item.text
                        elif name == "ChrStart":
                            coords["start"] = int(sub_item.text)
                        elif name == "ChrStop":
                            coords["end"] = int(sub_item.text)
                    
                    if len(coords) == 3:
                        return coords
        return None
        
    except Exception as e:
        logger.error(f"Coordinates error: {e}")
        return None

async def fetch_sequence(chromosome: str, start: int, end: int) -> str:
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
        response = await http_request(url)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Sequence fetch error: {e}")
        return None

async def http_request(url: str) -> str:
    """Make HTTP request"""
    loop = asyncio.get_event_loop()
    
    def make_request():
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode('utf-8')
    
    return await loop.run_in_executor(None, make_request)

async def main():
    """Main server function"""
    print("Starting Gene-to-Genomic MCP Server...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        print("Server initialized, waiting for connections...", file=sys.stderr)
        
        # Pass empty initialization options
        init_options = {}
        await server.run(
            read_stream, 
            write_stream, 
            init_options
        )

if __name__ == "__main__":
    asyncio.run(main())