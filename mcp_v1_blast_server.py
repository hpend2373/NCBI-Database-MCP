#!/usr/bin/env python3

import asyncio
import subprocess
import tempfile
import os
import sys
import logging
from typing import Any, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("bio-blast-mcp")

@server.list_tools()
async def list_tools():
    """List available tools"""
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
                        "description": "Target database name (e.g., 'nt', 'nr')",
                        "default": "nt"
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
                "required": ["query"]
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
                        "description": "Target database name (e.g., 'nr', 'swissprot')",
                        "default": "nr"
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
                "required": ["query"]
            }
        ),
        Tool(
            name="echo",
            description="Echo back the input message for testing",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back"
                    }
                },
                "required": ["message"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any):
    """Handle tool calls"""
    try:
        if name == "echo":
            message = arguments.get("message", "")
            return [TextContent(text=f"✅ Echo: {message}")]
        elif name == "blastn":
            result = await run_blast("blastn", arguments)
            return [TextContent(text=result)]
        elif name == "blastp":
            result = await run_blast("blastp", arguments)
            return [TextContent(text=result)]
        else:
            return [TextContent(text=f"❌ Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [TextContent(text=f"❌ Error: {str(e)}")]

async def run_blast(blast_type: str, arguments: dict) -> str:
    """Run BLAST search and return formatted results"""
    
    query = arguments["query"]
    database = arguments.get("database", "nt" if blast_type == "blastn" else "nr")
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
            return f"❌ BLAST failed: {result.stderr}"
        
        # Format results
        if not result.stdout.strip():
            return f"✅ BLAST {blast_type.upper()} search completed - No significant hits found for query in {database} database"
        
        # Parse and format results
        lines = result.stdout.strip().split('\n')
        formatted_results = f"✅ BLAST {blast_type.upper()} Results (Database: {database})\n"
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
    except FileNotFoundError:
        return f"❌ {blast_type} command not found. Please ensure BLAST+ is installed and in PATH"
    except Exception as e:
        return f"❌ Error running BLAST: {str(e)}"
    finally:
        # Clean up temporary file
        try:
            os.unlink(query_file)
        except:
            pass

async def main():
    """Main server function"""
    print("Starting BLAST MCP Server (v1.0)...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        print("Server initialized, waiting for connections...", file=sys.stderr)
        await server.run(read_stream, write_stream, {})

if __name__ == "__main__":
    asyncio.run(main())