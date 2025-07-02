#!/usr/bin/env python3
"""Test v2 server with manual MCP protocol"""

import asyncio
import json
import subprocess
import sys

async def test_v2_server():
    """Test v2 server with proper MCP protocol"""
    
    # Start server process
    process = await asyncio.create_subprocess_exec(
        sys.executable, "src/gene_server_v2.py",
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
        
        print("Sending initialize message...")
        process.stdin.write((json.dumps(init_message) + "\n").encode())
        await process.stdin.drain()
        
        # Read response
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        if response_line:
            response = json.loads(response_line.decode().strip())
            print(f"Initialize response: {response}")
            
            if "result" in response:
                # Step 2: List tools
                tools_message = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                
                print("Sending tools/list message...")
                process.stdin.write((json.dumps(tools_message) + "\n").encode())
                await process.stdin.drain()
                
                tools_response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                if tools_response_line:
                    tools_response = json.loads(tools_response_line.decode().strip())
                    print(f"Tools response: {tools_response}")
                    
                    if "result" in tools_response:
                        # Step 3: Call tool
                        call_message = {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "gene_to_sequence",
                                "arguments": {
                                    "gene_name": "TP53",
                                    "organism": "human"
                                }
                            }
                        }
                        
                        print("Sending tools/call message...")
                        process.stdin.write((json.dumps(call_message) + "\n").encode())
                        await process.stdin.drain()
                        
                        call_response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
                        if call_response_line:
                            call_response = json.loads(call_response_line.decode().strip())
                            print("Tool call response received!")
                            if "result" in call_response:
                                content = call_response["result"]["content"][0]["text"]
                                print(f"Result (first 200 chars): {content[:200]}...")
                                return True
        
        return False
        
    except asyncio.TimeoutError:
        print("Timeout waiting for server response")
        return False
    except Exception as e:
        print(f"Test error: {e}")
        return False
    finally:
        process.terminate()
        await process.wait()

async def main():
    print("Testing Gene Server v2 MCP Protocol...")
    
    success = await test_v2_server()
    
    print(f"MCP Protocol Test: {'PASSED' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)