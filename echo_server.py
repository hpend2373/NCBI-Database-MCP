#!/usr/bin/env python3

import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("echo-server")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="echo",
            description="Echo back the input message",
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
async def call_tool(name: str, arguments: dict):
    if name == "echo":
        message = arguments.get("message", "")
        return [TextContent(text=f"Echo: {message}")]
    else:
        return [TextContent(text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, {})

if __name__ == "__main__":
    asyncio.run(main())