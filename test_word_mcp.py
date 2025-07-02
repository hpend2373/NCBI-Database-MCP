#!/usr/bin/env python3
"""Test Word MCP Server functionality"""

import asyncio
import json
import subprocess
import sys
import os

async def test_word_mcp():
    """Test Word MCP Server operations"""
    
    print("🔧 Testing Word MCP Server...")
    print("=" * 50)
    
    # Set up environment
    env = os.environ.copy()
    env['DOCUMENT_DIR'] = '/Users/minyeop/alphagenome/bio-mcp-blast/WordDocuments'
    env['PYTHONPATH'] = '/Users/minyeop/alphagenome/bio-mcp-blast/Office-Word-MCP-Server'
    
    server_cmd = [
        "/Users/minyeop/alphagenome/bio-mcp-blast/Office-Word-MCP-Server/word_venv/bin/python",
        "/Users/minyeop/alphagenome/bio-mcp-blast/Office-Word-MCP-Server/word_mcp_server.py"
    ]
    
    cwd = "/Users/minyeop/alphagenome/bio-mcp-blast/WordDocuments"
    
    # Start server process
    process = await asyncio.create_subprocess_exec(
        *server_cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env
    )
    
    try:
        # Initialize
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "word-test", "version": "1.0.0"}
            }
        }
        
        process.stdin.write((json.dumps(init_message) + "\n").encode())
        await process.stdin.drain()
        
        # Read init response
        init_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        init_response = json.loads(init_line.decode().strip())
        
        if "result" in init_response:
            print("✅ MCP connection established")
            
            # List available tools
            tools_message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            process.stdin.write((json.dumps(tools_message) + "\n").encode())
            await process.stdin.drain()
            
            tools_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            tools_response = json.loads(tools_line.decode().strip())
            
            if "result" in tools_response:
                tools = tools_response["result"]["tools"]
                print(f"\n📋 Available tools ({len(tools)}):")
                for tool in tools[:5]:  # Show first 5 tools
                    print(f"  - {tool['name']}: {tool['description'][:60]}...")
                
                # Test creating a document
                create_message = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "create_document",
                        "arguments": {
                            "filename": "test_document.docx",
                            "title": "Test Document",
                            "author": "Word MCP Test"
                        }
                    }
                }
                
                print("\n📝 Creating test document...")
                process.stdin.write((json.dumps(create_message) + "\n").encode())
                await process.stdin.drain()
                
                create_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
                create_response = json.loads(create_line.decode().strip())
                
                if "result" in create_response:
                    content = create_response["result"]["content"][0]["text"]
                    print(f"✅ {content}")
                    
                    # Check if file was created
                    doc_path = os.path.join(env['DOCUMENT_DIR'], "test_document.docx")
                    if os.path.exists(doc_path):
                        print(f"✅ Document verified at: {doc_path}")
                        print(f"📏 File size: {os.path.getsize(doc_path)} bytes")
                        
                        # Clean up
                        os.remove(doc_path)
                        print("🧹 Test document cleaned up")
                        
                        return True
                    else:
                        print("❌ Document file not found!")
                        return False
                else:
                    print("❌ Document creation failed")
                    if "error" in create_response:
                        print(f"Error: {create_response['error']}")
                    return False
            else:
                print("❌ Tools list failed")
                return False
        else:
            print("❌ Initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        
        # Check stderr for errors
        stderr_data = await process.stderr.read()
        if stderr_data:
            print(f"Server errors:\n{stderr_data.decode()}")
        
        return False
    finally:
        process.terminate()
        await process.wait()

async def main():
    print("🔬 WORD MCP SERVER TEST")
    print("=" * 50)
    
    success = await test_word_mcp()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ WORD MCP TEST: PASSED")
        print("\n🎯 Next steps:")
        print("1. Restart Claude Desktop")
        print("2. Try: 'Create a new Word document'")
        print("3. Documents will be saved in:")
        print("   /Users/minyeop/alphagenome/bio-mcp-blast/WordDocuments/")
    else:
        print("❌ WORD MCP TEST: FAILED")
        print("🔧 Check the configuration and try again")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)