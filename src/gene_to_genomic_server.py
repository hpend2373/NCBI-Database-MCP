import asyncio
import json
import logging
import os
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Literal

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent
from mcp import McpError
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class ServerSettings(BaseSettings):
    max_file_size: int = Field(default=100_000_000, description="Maximum input file size in bytes")
    temp_dir: Optional[str] = Field(default=None, description="Temporary directory for processing")
    timeout: int = Field(default=300, description="Command timeout in seconds")
    ncbi_base_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils", description="NCBI E-utilities base URL")
    ncbi_api_key: Optional[str] = Field(default=None, description="NCBI API key for higher request limits (optional but recommended)")
    
    class Config:
        env_prefix = "BIO_MCP_"


class GeneToGenomicServer:
    def __init__(self, settings: Optional[ServerSettings] = None):
        self.settings = settings or ServerSettings()
        self.server = Server("bio-mcp-gene-to-genomic", version="0.1.0")
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="gene_to_genomic_sequence",
                    description="Convert gene name to genomic DNA sequence using NCBI E-utilities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "gene_name": {
                                "type": "string", 
                                "description": "Gene symbol or name (e.g., TP53, BRCA1)"
                            },
                            "organism": {
                                "type": "string",
                                "description": "Organism name (default: human)",
                                "default": "human"
                            },
                            "sequence_type": {
                                "type": "string",
                                "enum": ["genomic", "cds", "mrna", "protein"],
                                "description": "Type of sequence to retrieve (default: genomic)",
                                "default": "genomic"
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["fasta", "genbank", "json"],
                                "description": "Output format (default: fasta)",
                                "default": "fasta"
                            }
                        },
                        "required": ["gene_name"]
                    }
                ),
                Tool(
                    name="search_gene_info",
                    description="Search for gene information including genomic location",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "gene_name": {
                                "type": "string", 
                                "description": "Gene symbol or name"
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
                    name="get_genomic_sequence",
                    description="Get genomic sequence from chromosome coordinates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chromosome": {
                                "type": "string",
                                "description": "Chromosome accession (e.g., NC_000017.11)"
                            },
                            "start": {
                                "type": "integer",
                                "description": "Start position"
                            },
                            "end": {
                                "type": "integer",
                                "description": "End position"
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["fasta", "genbank"],
                                "description": "Output format (default: fasta)",
                                "default": "fasta"
                            }
                        },
                        "required": ["chromosome", "start", "end"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent]:
            if name == "gene_to_genomic_sequence":
                return await self._gene_to_genomic_sequence(arguments)
            elif name == "search_gene_info":
                return await self._search_gene_info(arguments)
            elif name == "get_genomic_sequence":
                return await self._get_genomic_sequence(arguments)
            else:
                raise McpError(f"Unknown tool: {name}")
    
    async def _gene_to_genomic_sequence(self, arguments: dict) -> list[TextContent]:
        """Main workflow: gene name -> genomic sequence"""
        try:
            gene_name = arguments["gene_name"]
            organism = arguments.get("organism", "human")
            sequence_type = arguments.get("sequence_type", "genomic")
            output_format = arguments.get("output_format", "fasta")
            
            # Step 1: Search for gene ID
            gene_info = await self._search_gene_ncbi(gene_name, organism)
            if not gene_info:
                return [TextContent(type="text", text=f"Gene '{gene_name}' not found in {organism}")]
            
            gene_id = gene_info.get("gene_id")
            if not gene_id:
                return [TextContent(type="text", text=f"Could not find gene ID for '{gene_name}'")]
            
            # Step 2: Get genomic coordinates
            genomic_info = await self._get_gene_genomic_info(gene_id)
            if not genomic_info:
                return [TextContent(type="text", text=f"Could not find genomic location for gene ID {gene_id}")]
            
            chromosome = genomic_info.get("chromosome")
            start_pos = genomic_info.get("start")
            end_pos = genomic_info.get("end")
            
            if not all([chromosome, start_pos, end_pos]):
                return [TextContent(type="text", text=f"Incomplete genomic coordinates for gene {gene_name}")]
            
            # Step 3: Get sequence
            if sequence_type == "genomic":
                sequence = await self._fetch_genomic_sequence(chromosome, start_pos, end_pos, output_format)
            else:
                # For other sequence types, we'd need additional logic
                sequence = await self._fetch_genomic_sequence(chromosome, start_pos, end_pos, output_format)
            
            if not sequence:
                return [TextContent(type="text", text=f"Could not retrieve sequence for {gene_name}")]
            
            # Format result
            result = f"Gene: {gene_name} ({organism})\n"
            result += f"Gene ID: {gene_id}\n"
            result += f"Location: {chromosome}:{start_pos}-{end_pos}\n"
            result += f"Sequence Type: {sequence_type}\n"
            result += f"Output Format: {output_format}\n\n"
            result += sequence
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            logger.error(f"Error in gene_to_genomic_sequence: {e}", exc_info=True)
            raise McpError(f"Error: {str(e)}")
    
    async def _search_gene_info(self, arguments: dict) -> list[TextContent]:
        """Search for gene information"""
        try:
            gene_name = arguments["gene_name"]
            organism = arguments.get("organism", "human")
            
            gene_info = await self._search_gene_ncbi(gene_name, organism)
            if not gene_info:
                return [TextContent(type="text", text=f"Gene '{gene_name}' not found in {organism}")]
            
            result = json.dumps(gene_info, indent=2)
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            logger.error(f"Error searching gene info: {e}", exc_info=True)
            raise McpError(f"Error: {str(e)}")
    
    async def _get_genomic_sequence(self, arguments: dict) -> list[TextContent]:
        """Get genomic sequence from coordinates"""
        try:
            chromosome = arguments["chromosome"]
            start = arguments["start"]
            end = arguments["end"]
            output_format = arguments.get("output_format", "fasta")
            
            sequence = await self._fetch_genomic_sequence(chromosome, start, end, output_format)
            if not sequence:
                return [TextContent(type="text", text=f"Could not retrieve sequence from {chromosome}:{start}-{end}")]
            
            return [TextContent(type="text", text=sequence)]
            
        except Exception as e:
            logger.error(f"Error getting genomic sequence: {e}", exc_info=True)
            raise McpError(f"Error: {str(e)}")
    
    async def _search_gene_ncbi(self, gene_name: str, organism: str) -> Optional[dict]:
        """Search for gene in NCBI Gene database"""
        try:
            # Build search query
            query = f"{gene_name}[GENE] AND {organism}[ORGN]"
            url = f"{self.settings.ncbi_base_url}/esearch.fcgi"
            params = {
                "db": "gene",
                "term": query,
                "retmode": "xml",
                "retmax": "1"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            # Make request
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            # Parse XML response
            root = ET.fromstring(response)
            id_list = root.find("IdList")
            if id_list is None or len(id_list) == 0:
                return None
            
            gene_id = id_list.find("Id").text
            
            # Get detailed information
            summary_info = await self._get_gene_summary(gene_id)
            
            return {
                "gene_id": gene_id,
                "gene_name": gene_name,
                "organism": organism,
                **summary_info
            }
            
        except Exception as e:
            logger.error(f"Error searching gene in NCBI: {e}")
            return None
    
    async def _get_gene_summary(self, gene_id: str) -> dict:
        """Get gene summary information"""
        try:
            url = f"{self.settings.ncbi_base_url}/esummary.fcgi"
            params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "xml"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            # Parse XML and extract relevant information
            root = ET.fromstring(response)
            doc_sum = root.find("DocSum")
            
            summary = {}
            if doc_sum is not None:
                for item in doc_sum.findall("Item"):
                    name = item.get("Name")
                    if name in ["Description", "OfficialSymbol", "Chromosome", "MapLocation"]:
                        summary[name.lower()] = item.text
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting gene summary: {e}")
            return {}
    
    async def _get_gene_genomic_info(self, gene_id: str) -> Optional[dict]:
        """Get genomic coordinates for a gene"""
        try:
            url = f"{self.settings.ncbi_base_url}/esummary.fcgi"
            params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "xml"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            # Parse XML to extract genomic info
            root = ET.fromstring(response)
            doc_sum = root.find("DocSum")
            
            if doc_sum is None:
                return None
            
            # Look for GenomicInfo
            for item in doc_sum.findall("Item"):
                if item.get("Name") == "GenomicInfo":
                    genomic_info = {}
                    for sub_item in item.findall("Item"):
                        name = sub_item.get("Name")
                        if name == "ChrAccVer":
                            genomic_info["chromosome"] = sub_item.text
                        elif name == "ChrStart":
                            genomic_info["start"] = int(sub_item.text)
                        elif name == "ChrStop":
                            genomic_info["end"] = int(sub_item.text)
                    
                    if all(k in genomic_info for k in ["chromosome", "start", "end"]):
                        return genomic_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting genomic info: {e}")
            return None
    
    async def _fetch_genomic_sequence(self, chromosome: str, start: int, end: int, format_type: str = "fasta") -> Optional[str]:
        """Fetch genomic sequence from NCBI"""
        try:
            url = f"{self.settings.ncbi_base_url}/efetch.fcgi"
            params = {
                "db": "nuccore",
                "id": chromosome,
                "seq_start": str(start),
                "seq_stop": str(end),
                "rettype": "fasta" if format_type == "fasta" else "gb",
                "retmode": "text"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error fetching genomic sequence: {e}")
            return None
    
    async def _make_http_request(self, url: str) -> str:
        """Make HTTP request with timeout"""
        try:
            # Use asyncio to make the request non-blocking
            loop = asyncio.get_event_loop()
            
            def make_request():
                with urllib.request.urlopen(url, timeout=self.settings.timeout) as response:
                    return response.read().decode('utf-8')
            
            result = await loop.run_in_executor(None, make_request)
            return result
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream, 
                {
                    "name": "bio-mcp-gene-to-genomic",
                    "version": "0.1.0"
                }
            )


async def main():
    import sys
    logging.basicConfig(level=logging.DEBUG)
    print("Starting bio-mcp-gene-to-genomic server...", file=sys.stderr)
    server = GeneToGenomicServer()
    print("Server initialized, starting run...", file=sys.stderr)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())