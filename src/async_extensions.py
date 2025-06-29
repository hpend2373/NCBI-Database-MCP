"""
Extended BLAST MCP server with async job support
"""
import asyncio
import uuid
from typing import Any, Optional
from pathlib import Path
import httpx

from mcp.types import Tool, TextContent, ErrorContent
from pydantic import BaseModel, Field

# Import the original server
from .server import BlastServer as BaseBlastServer


class AsyncBlastServer(BaseBlastServer):
    """Extended BLAST server with async job submission"""
    
    def __init__(self, settings=None, queue_url: Optional[str] = None):
        super().__init__(settings)
        self.queue_url = queue_url or "http://localhost:8000"
        self._setup_async_handlers()
    
    def _setup_async_handlers(self):
        """Add async job handlers to the existing tools"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            # Get base tools
            base_tools = await super(AsyncBlastServer, self).server.list_tools()
            
            # Add async variants
            async_tools = [
                Tool(
                    name="blastn_async",
                    description="Submit nucleotide BLAST search as background job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Path to query FASTA file"
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
                            "notification_email": {
                                "type": "string",
                                "description": "Email for job completion notification"
                            }
                        },
                        "required": ["query", "database"]
                    }
                ),
                Tool(
                    name="get_job_status",
                    description="Check status of async job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID to check"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="get_job_result",
                    description="Retrieve results of completed job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID to retrieve results for"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
            ]
            
            return base_tools + async_tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent | ErrorContent]:
            # Handle async tools
            if name == "blastn_async":
                return await self._submit_blast_job(arguments, "blastn")
            elif name == "get_job_status":
                return await self._get_job_status(arguments["job_id"])
            elif name == "get_job_result":
                return await self._get_job_result(arguments["job_id"])
            else:
                # Delegate to parent class
                return await super(AsyncBlastServer, self).server.call_tool(name, arguments)
    
    async def _submit_blast_job(self, arguments: dict, blast_type: str) -> list[TextContent | ErrorContent]:
        """Submit BLAST job to queue"""
        try:
            # Generate job ID
            job_id = str(uuid.uuid4())
            
            # Prepare job request
            job_request = {
                "job_id": job_id,
                "job_type": blast_type,
                "parameters": arguments,
                "priority": 5
            }
            
            # Submit to queue API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.queue_url}/jobs/submit",
                    json=job_request,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return [ErrorContent(text=f"Failed to submit job: {response.text}")]
                
                job_info = response.json()
                
                return [TextContent(
                    text=f"Job submitted successfully!\n\n"
                         f"Job ID: {job_info['job_id']}\n"
                         f"Status: {job_info['status']}\n"
                         f"Queue: {blast_type}\n\n"
                         f"Use 'get_job_status' with this job ID to check progress."
                )]
                
        except Exception as e:
            return [ErrorContent(text=f"Error submitting job: {str(e)}")]
    
    async def _get_job_status(self, job_id: str) -> list[TextContent | ErrorContent]:
        """Get job status from queue"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.queue_url}/jobs/{job_id}/status",
                    timeout=10.0
                )
                
                if response.status_code == 404:
                    return [ErrorContent(text=f"Job {job_id} not found")]
                elif response.status_code != 200:
                    return [ErrorContent(text=f"Failed to get job status: {response.text}")]
                
                job_info = response.json()
                
                status_text = f"Job ID: {job_info['job_id']}\n"
                status_text += f"Status: {job_info['status']}\n"
                status_text += f"Created: {job_info['created_at']}\n"
                
                if job_info.get('started_at'):
                    status_text += f"Started: {job_info['started_at']}\n"
                
                if job_info.get('progress'):
                    status_text += f"Progress: {job_info['progress']}%\n"
                
                if job_info['status'] == 'completed':
                    status_text += f"Completed: {job_info['completed_at']}\n"
                    status_text += "\nUse 'get_job_result' to retrieve the results."
                elif job_info['status'] == 'failed':
                    status_text += f"Failed: {job_info.get('error', 'Unknown error')}\n"
                
                return [TextContent(text=status_text)]
                
        except Exception as e:
            return [ErrorContent(text=f"Error checking job status: {str(e)}")]
    
    async def _get_job_result(self, job_id: str) -> list[TextContent | ErrorContent]:
        """Get job results from storage"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.queue_url}/jobs/{job_id}/result",
                    timeout=30.0
                )
                
                if response.status_code == 404:
                    return [ErrorContent(text=f"Job {job_id} not found")]
                elif response.status_code != 200:
                    return [ErrorContent(text=f"Failed to get job result: {response.text}")]
                
                result = response.json()
                
                if result['status'] != 'completed':
                    return [ErrorContent(text=f"Job is not completed yet. Status: {result['status']}")]
                
                # For demo, return summary + download link
                result_text = f"Job {job_id} Results\n"
                result_text += "=" * 40 + "\n\n"
                
                if 'summary' in result:
                    result_text += "Summary:\n"
                    for key, value in result['summary'].items():
                        result_text += f"  {key}: {value}\n"
                    result_text += "\n"
                
                result_text += f"Full results available at:\n{result['result_url']}\n"
                result_text += "\nResults will be available for 7 days."
                
                return [TextContent(text=result_text)]
                
        except Exception as e:
            return [ErrorContent(text=f"Error retrieving job results: {str(e)}")]