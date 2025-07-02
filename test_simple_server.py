#!/usr/bin/env python3
"""Simple MCP server test"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

async def main():
    # Create server
    server = Server("test-server", version="1.0.0")
    
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="echo",
                description="Echo back the input",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    },
                    "required": ["message"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "echo":
            return [TextContent(text=f"Echo: {arguments['message']}")]
        else:
            return [TextContent(text=f"Unknown tool: {name}")]
    
    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, {})

if __name__ == "__main__":
    asyncio.run(main())