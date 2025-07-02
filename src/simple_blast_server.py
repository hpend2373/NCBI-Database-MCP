#!/usr/bin/env python3
"""
Simple BLAST MCP Server
"""

import asyncio
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp import McpError, ErrorData

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server instance
server = Server("bio-mcp-blast")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available BLAST tools"""
    return [
        Tool(
            name="blastn",
            description="Nucleotide-nucleotide BLAST search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query sequence (FASTA format or raw sequence)"
                    },
                    "database": {
                        "type": "string",
                        "description": "Target database name (e.g., 'nt', 'nr')"
                    },
                    "evalue": {
                        "type": "number",
                        "description": "E-value threshold",
                        "default": 10
                    },
                    "max_hits": {
                        "type": "integer",
                        "description": "Maximum number of hits to return",
                        "default": 10
                    }
                },
                "required": ["query", "database"]
            }
        ),
        Tool(
            name="blastp",
            description="Protein-protein BLAST search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query sequence (FASTA format or raw sequence)"
                    },
                    "database": {
                        "type": "string",
                        "description": "Target database name (e.g., 'nr', 'swissprot')"
                    },
                    "evalue": {
                        "type": "number",
                        "description": "E-value threshold",
                        "default": 10
                    },
                    "max_hits": {
                        "type": "integer",
                        "description": "Maximum number of hits to return",
                        "default": 10
                    }
                },
                "required": ["query", "database"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "blastn":
            return await run_blast("blastn", arguments)
        elif name == "blastp":
            return await run_blast("blastp", arguments)
        else:
            raise McpError(
                ErrorData(code="invalid_tool", message=f"Unknown tool: {name}")
            )
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [TextContent(text=f"❌ Error: {str(e)}")]

async def run_blast(blast_type: str, arguments: dict) -> list[TextContent]:
    """Run BLAST search"""
    query = arguments["query"]
    database = arguments["database"]
    evalue = arguments.get("evalue", 10)
    max_hits = arguments.get("max_hits", 10)
    
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
            return [TextContent(text=f"❌ BLAST failed: {result.stderr}")]
        
        # Format results
        if not result.stdout.strip():
            return [TextContent(text="✅ BLAST search completed - No significant hits found")]
        
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
        
        return [TextContent(text=formatted_results)]
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(query_file)
        except:
            pass

async def main():
    """Main server function"""
    print("Starting BLAST MCP Server...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        print("Server initialized, waiting for connections...", file=sys.stderr)
        await server.run(read_stream, write_stream, {})

if __name__ == "__main__":
    asyncio.run(main())