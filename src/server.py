import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Literal

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, ErrorContent
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class ServerSettings(BaseSettings):
    max_file_size: int = Field(default=100_000_000, description="Maximum input file size in bytes")
    temp_dir: Optional[str] = Field(default=None, description="Temporary directory for processing")
    timeout: int = Field(default=300, description="Command timeout in seconds")
    blast_path: str = Field(default="blastn", description="Path to BLAST executable")
    
    class Config:
        env_prefix = "BIO_MCP_"


class BlastServer:
    def __init__(self, settings: Optional[ServerSettings] = None):
        self.settings = settings or ServerSettings()
        self.server = Server("bio-mcp-blast")
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="blastn",
                    description="Nucleotide-nucleotide BLAST search",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string", 
                                "description": "Path to query FASTA file or sequence string"
                            },
                            "database": {
                                "type": "string",
                                "description": "Path to BLAST database or name of NCBI database"
                            },
                            "evalue": {
                                "type": "number",
                                "description": "E-value threshold (default: 10)",
                                "default": 10
                            },
                            "max_hits": {
                                "type": "integer",
                                "description": "Maximum number of hits to return (default: 50)",
                                "default": 50
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["tabular", "xml", "json", "pairwise"],
                                "description": "Output format (default: tabular)",
                                "default": "tabular"
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
                                "description": "Path to query FASTA file or sequence string"
                            },
                            "database": {
                                "type": "string",
                                "description": "Path to BLAST database or name of NCBI database"
                            },
                            "evalue": {
                                "type": "number",
                                "description": "E-value threshold (default: 10)",
                                "default": 10
                            },
                            "max_hits": {
                                "type": "integer",
                                "description": "Maximum number of hits to return (default: 50)",
                                "default": 50
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["tabular", "xml", "json", "pairwise"],
                                "description": "Output format (default: tabular)",
                                "default": "tabular"
                            }
                        },
                        "required": ["query", "database"]
                    }
                ),
                Tool(
                    name="makeblastdb",
                    description="Create a BLAST database from FASTA file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to input FASTA file"
                            },
                            "database_name": {
                                "type": "string",
                                "description": "Name for the output database"
                            },
                            "dbtype": {
                                "type": "string",
                                "enum": ["nucl", "prot"],
                                "description": "Database type: nucleotide or protein"
                            },
                            "title": {
                                "type": "string",
                                "description": "Title for the database (optional)"
                            }
                        },
                        "required": ["input_file", "database_name", "dbtype"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent | ErrorContent]:
            if name == "blastn":
                return await self._run_blast(arguments, "blastn")
            elif name == "blastp":
                return await self._run_blast(arguments, "blastp")
            elif name == "makeblastdb":
                return await self._make_blast_db(arguments)
            else:
                return [ErrorContent(text=f"Unknown tool: {name}")]
    
    async def _run_blast(self, arguments: dict, blast_type: str) -> list[TextContent | ErrorContent]:
        try:
            query = arguments["query"]
            database = arguments["database"]
            evalue = arguments.get("evalue", 10)
            max_hits = arguments.get("max_hits", 50)
            output_format = arguments.get("output_format", "tabular")
            
            # Map output formats to BLAST outfmt codes
            format_map = {
                "tabular": "6",
                "xml": "5",
                "json": "15",
                "pairwise": "0"
            }
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                # Handle query - could be file path or sequence
                query_file = Path(tmpdir) / "query.fasta"
                
                if Path(query).exists():
                    # It's a file
                    query_path = Path(query)
                    if query_path.stat().st_size > self.settings.max_file_size:
                        return [ErrorContent(text=f"Query file too large. Maximum size: {self.settings.max_file_size} bytes")]
                    query_file.write_bytes(query_path.read_bytes())
                else:
                    # It's a sequence string
                    if not query.startswith(">"):
                        query = ">Query\n" + query
                    query_file.write_text(query)
                
                # Build command
                cmd = [
                    blast_type,
                    "-query", str(query_file),
                    "-db", database,
                    "-evalue", str(evalue),
                    "-max_target_seqs", str(max_hits),
                    "-outfmt", format_map[output_format]
                ]
                
                # Execute command
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.settings.timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return [ErrorContent(text=f"BLAST search timed out after {self.settings.timeout} seconds")]
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"BLAST failed: {stderr.decode()}")]
                
                output = stdout.decode()
                
                # Add header for tabular format
                if output_format == "tabular" and output:
                    header = "# Fields: query_id, subject_id, percent_identity, alignment_length, mismatches, gap_opens, q_start, q_end, s_start, s_end, evalue, bit_score\n"
                    output = header + output
                
                return [TextContent(text=output)]
                
        except Exception as e:
            logger.error(f"Error running BLAST: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def _make_blast_db(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            database_name = arguments["database_name"]
            dbtype = arguments["dbtype"]
            title = arguments.get("title", database_name)
            
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            if input_file.stat().st_size > self.settings.max_file_size:
                return [ErrorContent(text=f"File too large. Maximum size: {self.settings.max_file_size} bytes")]
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                # Copy input file
                temp_input = Path(tmpdir) / input_file.name
                temp_input.write_bytes(input_file.read_bytes())
                
                # Output database path
                db_path = Path(tmpdir) / database_name
                
                # Build command
                cmd = [
                    "makeblastdb",
                    "-in", str(temp_input),
                    "-out", str(db_path),
                    "-dbtype", dbtype,
                    "-title", title
                ]
                
                # Execute command
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"makeblastdb failed: {stderr.decode()}")]
                
                # List created files
                created_files = list(Path(tmpdir).glob(f"{database_name}.*"))
                file_list = "\n".join([f.name for f in created_files])
                
                return [TextContent(
                    text=f"BLAST database created successfully!\n\n"
                         f"Output:\n{stdout.decode()}\n\n"
                         f"Created files:\n{file_list}"
                )]
                
        except Exception as e:
            logger.error(f"Error creating BLAST database: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    logging.basicConfig(level=logging.INFO)
    server = BlastServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())