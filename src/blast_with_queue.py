"""
BLAST MCP server with queue integration
This extends the base BLAST server to support async job submission
"""
from typing import Any, Optional
from mcp.types import TextContent, ErrorContent
from .server import BlastServer
import sys
import os

# Add the template directory to path to import queue integration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bio-mcp-template/src'))
from queue_integration import QueueIntegrationMixin


class BlastServerWithQueue(QueueIntegrationMixin, BlastServer):
    """BLAST server with async job queue support"""
    
    def __init__(self, settings=None, queue_url: Optional[str] = None):
        self.queue_url = queue_url or "http://localhost:8000"
        super().__init__(settings)
        self._setup_async_handlers()
    
    def _setup_async_handlers(self):
        """Add async handlers to existing BLAST tools"""
        
        # Define async variants for BLAST tools
        async_tool_configs = {
            "blastn": {
                "job_type": "blastn",
                "description": "Nucleotide BLAST search",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Path to query FASTA file or sequence string"
                    },
                    "database": {
                        "type": "string",
                        "description": "Database name"
                    },
                    "evalue": {
                        "type": "number",
                        "default": 10
                    },
                    "max_hits": {
                        "type": "integer", 
                        "default": 50
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["tabular", "xml", "json", "pairwise"],
                        "default": "json"
                    }
                },
                "required_params": ["query", "database"]
            },
            "blastp": {
                "job_type": "blastp", 
                "description": "Protein BLAST search",
                "parameters": {
                    "query": {"type": "string", "description": "Query file or sequence"},
                    "database": {"type": "string", "description": "Database name"},
                    "evalue": {"type": "number", "default": 10},
                    "max_hits": {"type": "integer", "default": 50},
                    "output_format": {
                        "type": "string",
                        "enum": ["tabular", "xml", "json", "pairwise"],
                        "default": "json"
                    }
                },
                "required_params": ["query", "database"]
            },
            "makeblastdb": {
                "job_type": "makeblastdb",
                "description": "Create BLAST database",
                "parameters": {
                    "input_file": {"type": "string", "description": "Input FASTA file"},
                    "database_name": {"type": "string", "description": "Database name"},
                    "dbtype": {"type": "string", "enum": ["nucl", "prot"]},
                    "title": {"type": "string", "description": "Database title"}
                },
                "required_params": ["input_file", "database_name", "dbtype"]
            }
        }
        
        @self.server.list_tools()
        async def list_tools():
            # Get base BLAST tools
            base_tools = await super(BlastServerWithQueue, self).server.list_tools()
            
            # Add async variants
            async_tools = self.get_async_tools(async_tool_configs)
            
            return base_tools + async_tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any):
            # Handle async BLAST tools
            if name in ["blastn_async", "blastp_async", "makeblastdb_async"]:
                base_name = name[:-6]  # Remove _async suffix
                return await self._handle_blast_async(base_name, arguments)
            
            # Handle job management
            elif name == "get_job_status":
                return await self._handle_job_status(arguments["job_id"])
            elif name == "get_job_result":
                return await self._handle_job_result(arguments["job_id"])
            elif name == "cancel_job":
                return await self._handle_cancel_job(arguments["job_id"])
            
            # Otherwise use parent's handler
            else:
                return await super(BlastServerWithQueue, self).server.call_tool(name, arguments)
    
    async def _handle_blast_async(self, tool_name: str, arguments: dict) -> list[TextContent | ErrorContent]:
        """Handle async BLAST job submission"""
        try:
            # Extract queue parameters
            priority = arguments.pop("priority", 5)
            tags = arguments.pop("tags", [])
            notification_email = arguments.pop("notification_email", None)
            
            # Add tool-specific tags
            tags.extend(["blast", tool_name])
            
            # Submit to queue
            job_info = await self.submit_job(
                job_type=tool_name,
                parameters=arguments,
                priority=priority,
                tags=tags
            )
            
            return [TextContent(
                text=f"🧬 BLAST Job Submitted!\n\n"
                     f"Job ID: {job_info['job_id']}\n"
                     f"Type: {tool_name.upper()}\n"
                     f"Status: {job_info['status']}\n"
                     f"Database: {arguments.get('database', 'N/A')}\n"
                     f"Priority: {priority}\n\n"
                     f"💡 Next steps:\n"
                     f"• Use 'get_job_status {job_info['job_id']}' to check progress\n"
                     f"• Use 'get_job_result {job_info['job_id']}' when completed\n\n"
                     f"Large BLAST searches typically take 2-30 minutes depending on database size."
            )]
            
        except Exception as e:
            return [ErrorContent(text=f"❌ Error submitting BLAST job: {str(e)}")]
    
    async def _handle_job_status(self, job_id: str) -> list[TextContent | ErrorContent]:
        """Enhanced job status for BLAST"""
        try:
            job_info = await self.get_job_status(job_id)
            
            # Format with BLAST-specific context
            status_text = f"🧬 BLAST Job Status\n"
            status_text += "=" * 30 + "\n\n"
            status_text += self.format_job_status(job_info)
            
            # Add BLAST-specific guidance
            if job_info['status'] == 'running':
                status_text += "\n💡 Your BLAST search is running on our compute cluster.\n"
                status_text += "Large database searches can take 5-30 minutes."
            elif job_info['status'] == 'completed':
                status_text += "\n✅ Ready! Use 'get_job_result' to see your BLAST hits."
            elif job_info['status'] == 'failed':
                status_text += "\n❌ Check your query sequence and database name."
            
            return [TextContent(text=status_text)]
            
        except Exception as e:
            return [ErrorContent(text=f"❌ Error checking job: {str(e)}")]
    
    async def _handle_job_result(self, job_id: str) -> list[TextContent | ErrorContent]:
        """Enhanced job results for BLAST"""
        try:
            result = await self.get_job_result(job_id)
            
            result_text = f"🧬 BLAST Results - Job {job_id}\n"
            result_text += "=" * 50 + "\n\n"
            
            # Show summary if available
            if "summary" in result:
                summary = result["summary"]
                result_text += "📊 Summary:\n"
                result_text += f"  Query: {summary.get('query_title', 'N/A')}\n"
                result_text += f"  Query Length: {summary.get('query_len', 'N/A')} bp/aa\n"
                result_text += f"  Database: {summary.get('database', 'N/A')}\n"
                result_text += f"  Total Hits: {summary.get('num_hits', 'N/A')}\n"
                
                if summary.get('best_hit_evalue'):
                    result_text += f"  Best Hit E-value: {summary['best_hit_evalue']}\n"
                if summary.get('best_hit_identity'):
                    result_text += f"  Best Hit Identity: {summary['best_hit_identity']}%\n"
                
                result_text += "\n"
            
            # Provide download link
            if "result_url" in result:
                result_text += f"📁 Full Results:\n"
                result_text += f"Download: {result['result_url']}\n\n"
                result_text += "💾 Results are available for 7 days.\n"
                result_text += "💡 You can open this URL in a browser or download with curl/wget."
            
            return [TextContent(text=result_text)]
            
        except Exception as e:
            return [ErrorContent(text=f"❌ Error retrieving results: {str(e)}")]
    
    async def _handle_cancel_job(self, job_id: str) -> list[TextContent | ErrorContent]:
        """Cancel BLAST job"""
        try:
            await self.cancel_job(job_id)
            return [TextContent(text=f"🛑 BLAST job {job_id} cancelled successfully")]
        except Exception as e:
            return [ErrorContent(text=f"❌ Error cancelling job: {str(e)}")]


# Example of how to use this
async def main():
    # Start server with queue support
    server = BlastServerWithQueue(queue_url="http://localhost:8000")
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())