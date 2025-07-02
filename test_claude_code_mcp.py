#!/usr/bin/env python3
"""Test MCP server that was configured for Claude Code"""

import asyncio
import json
import subprocess
import sys
import os

async def test_claude_code_mcp():
    """Test the MCP server configured for Claude Code"""
    
    print("🔧 Testing Gene-to-Genomic MCP Server for Claude Code...")
    
    # Use the exact command from Claude Code configuration
    server_cmd = [
        "/Users/minyeop/alphagenome/bio-mcp-blast/venv/bin/python",
        "src/gene_server_v2.py"
    ]
    
    # Change to the correct directory
    cwd = "/Users/minyeop/alphagenome/bio-mcp-blast"
    
    # Start server process
    process = await asyncio.create_subprocess_exec(
        *server_cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
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
                "clientInfo": {"name": "claude-code-test", "version": "1.0.0"}
            }
        }
        
        print("📤 Sending initialize message...")
        process.stdin.write((json.dumps(init_message) + "\n").encode())
        await process.stdin.drain()
        
        # Read response
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        if response_line:
            response = json.loads(response_line.decode().strip())
            print(f"📥 Initialize response: Success ✅")
            
            if "result" in response:
                # Step 2: List tools
                tools_message = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                
                print("📤 Sending tools/list message...")
                process.stdin.write((json.dumps(tools_message) + "\n").encode())
                await process.stdin.drain()
                
                tools_response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                if tools_response_line:
                    tools_response = json.loads(tools_response_line.decode().strip())
                    print(f"📥 Tools list response: Success ✅")
                    
                    if "result" in tools_response:
                        tools = tools_response["result"]["tools"]
                        print(f"🧬 Available tools: {[tool['name'] for tool in tools]}")
                        
                        # Step 3: Test tool call with a quick gene
                        call_message = {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "gene_to_sequence",
                                "arguments": {
                                    "gene_name": "INS",  # Insulin gene (smaller for quick test)
                                    "organism": "human"
                                }
                            }
                        }
                        
                        print("📤 Testing gene_to_sequence tool with INS gene...")
                        process.stdin.write((json.dumps(call_message) + "\n").encode())
                        await process.stdin.drain()
                        
                        call_response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
                        if call_response_line:
                            call_response = json.loads(call_response_line.decode().strip())
                            print("📥 Tool call response received! ✅")
                            
                            if "result" in call_response:
                                content = call_response["result"]["content"][0]["text"]
                                # Show summary
                                lines = content.split('\n')[:6]  # First 6 lines
                                print("📊 Result summary:")
                                for line in lines:
                                    if line.strip():
                                        print(f"  {line}")
                                
                                print("🎉 Claude Code MCP integration working perfectly!")
                                return True
        
        return False
        
    except asyncio.TimeoutError:
        print("⏰ Timeout waiting for server response")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    finally:
        process.terminate()
        await process.wait()

async def main():
    print("=" * 60)
    print("🧬 GENE-TO-GENOMIC MCP SERVER TEST FOR CLAUDE CODE")
    print("=" * 60)
    
    success = await test_claude_code_mcp()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ CLAUDE CODE MCP INTEGRATION: SUCCESS!")
        print("🎯 You can now use the gene-to-genomic tool in Claude Code")
        print("📝 Example usage in Claude Code:")
        print("   - Ask: 'Get the genomic sequence for TP53 gene'")
        print("   - Ask: 'Show me BRCA1 complete DNA sequence'")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ CLAUDE CODE MCP INTEGRATION: FAILED")
        print("🔧 Check server configuration and try again")
        print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)