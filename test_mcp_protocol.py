#!/usr/bin/env python3
"""Test MCP protocol directly"""

import asyncio
import json
import subprocess
import sys

async def test_mcp_server(server_path):
    """Test MCP server with proper initialization"""
    
    # Start server process
    process = await asyncio.create_subprocess_exec(
        sys.executable, server_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        # Step 1: Initialize
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        process.stdin.write((json.dumps(init_message) + "\n").encode())
        await process.stdin.drain()
        
        # Read response
        response_line = await process.stdout.readline()
        if response_line:
            response = json.loads(response_line.decode().strip())
            print(f"Initialize response: {response}")
            
            if "error" not in response:
                # Step 2: List tools
                tools_message = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                
                process.stdin.write((json.dumps(tools_message) + "\n").encode())
                await process.stdin.drain()
                
                tools_response_line = await process.stdout.readline()
                if tools_response_line:
                    tools_response = json.loads(tools_response_line.decode().strip())
                    print(f"Tools response: {tools_response}")
                    return True
        
        return False
        
    finally:
        process.terminate()
        await process.wait()

async def main():
    print("Testing Gene Server MCP Protocol...")
    
    server_path = "src/gene_server_final.py"
    success = await test_mcp_server(server_path)
    
    print(f"MCP Protocol Test: {'PASSED' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)