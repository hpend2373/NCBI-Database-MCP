#!/usr/bin/env python3
"""
Simple Gene-to-Genomic-Sequence MCP Server
Uses NCBI E-utilities to convert gene names to genomic sequences
"""

import asyncio
import json
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


logger = logging.getLogger(__name__)

# NCBI API Configuration
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"


class SimpleGeneServer:
    def __init__(self):
        self.server = Server("gene-to-genomic")
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="gene_to_sequence",
                    description="Convert gene name to genomic DNA sequence",
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
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            if name == "gene_to_sequence":
                return await self._gene_to_sequence(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    async def _gene_to_sequence(self, args: dict) -> list[TextContent]:
        try:
            gene_name = args["gene_name"]
            organism = args.get("organism", "human")
            
            # Step 1: Find gene ID
            gene_id = await self._search_gene(gene_name, organism)
            if not gene_id:
                return [TextContent(type="text", text=f"Gene '{gene_name}' not found")]
            
            # Step 2: Get genomic coordinates
            coords = await self._get_coordinates(gene_id)
            if not coords:
                return [TextContent(type="text", text=f"Coordinates not found for {gene_name}")]
            
            # Step 3: Get sequence
            sequence = await self._fetch_sequence(coords["chr"], coords["start"], coords["end"])
            if not sequence:
                return [TextContent(type="text", text=f"Sequence not found for {gene_name}")]
            
            result = f"Gene: {gene_name} ({organism})\n"
            result += f"Location: {coords['chr']}:{coords['start']}-{coords['end']}\n\n"
            result += sequence
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _search_gene(self, gene_name: str, organism: str) -> str:
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
            response = await self._http_request(url)
            
            root = ET.fromstring(response)
            id_list = root.find("IdList")
            if id_list is not None and len(id_list) > 0:
                return id_list.find("Id").text
            return None
            
        except Exception as e:
            logger.error(f"Gene search error: {e}")
            return None
    
    async def _get_coordinates(self, gene_id: str) -> dict:
        try:
            params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "xml",
                "api_key": NCBI_API_KEY
            }
            
            url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
            response = await self._http_request(url)
            
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
    
    async def _fetch_sequence(self, chromosome: str, start: int, end: int) -> str:
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
            response = await self._http_request(url)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Sequence fetch error: {e}")
            return None
    
    async def _http_request(self, url: str) -> str:
        loop = asyncio.get_event_loop()
        
        def make_request():
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode('utf-8')
        
        return await loop.run_in_executor(None, make_request)
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, {})


async def main():
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    print("Starting simple gene-to-genomic server...", file=sys.stderr)
    
    server = SimpleGeneServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())