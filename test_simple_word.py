#!/usr/bin/env python3
"""Test Simple Word MCP Server"""

import asyncio
import json
import subprocess
import sys
import os

async def test_simple_word_mcp():
    """Test Simple Word MCP Server operations"""
    
    print("🔧 Testing Simple Word MCP Server...")
    print("=" * 50)
    
    # Set up environment
    env = os.environ.copy()
    env['DOCUMENT_DIR'] = '/Users/minyeop/alphagenome/bio-mcp-blast/WordDocuments'
    
    server_cmd = [
        "/Users/minyeop/alphagenome/bio-mcp-blast/Office-Word-MCP-Server/word_venv/bin/python",
        "/Users/minyeop/alphagenome/bio-mcp-blast/Office-Word-MCP-Server/simple_word_server.py"
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
        init_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
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
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
                
                # Test 1: Create document
                create_message = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "create_document",
                        "arguments": {
                            "filename": "test_doc",
                            "title": "테스트 문서",
                            "content": "이것은 테스트 문서입니다."
                        }
                    }
                }
                
                print("\n📝 Test 1: Creating document...")
                process.stdin.write((json.dumps(create_message) + "\n").encode())
                await process.stdin.drain()
                
                create_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                create_response = json.loads(create_line.decode().strip())
                
                if "result" in create_response:
                    print(create_response["result"]["content"][0]["text"])
                
                # Test 2: Add paragraph
                add_message = {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "add_paragraph",
                        "arguments": {
                            "filename": "test_doc",
                            "text": "추가된 단락입니다.",
                            "style": "Normal"
                        }
                    }
                }
                
                print("\n📝 Test 2: Adding paragraph...")
                process.stdin.write((json.dumps(add_message) + "\n").encode())
                await process.stdin.drain()
                
                add_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                add_response = json.loads(add_line.decode().strip())
                
                if "result" in add_response:
                    print(add_response["result"]["content"][0]["text"])
                
                # Test 3: List documents
                list_message = {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "list_documents",
                        "arguments": {}
                    }
                }
                
                print("\n📁 Test 3: Listing documents...")
                process.stdin.write((json.dumps(list_message) + "\n").encode())
                await process.stdin.drain()
                
                list_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                list_response = json.loads(list_line.decode().strip())
                
                if "result" in list_response:
                    print(list_response["result"]["content"][0]["text"])
                
                # Clean up test file
                test_file = os.path.join(env['DOCUMENT_DIR'], "test_doc.docx")
                if os.path.exists(test_file):
                    os.remove(test_file)
                    print("\n🧹 Test document cleaned up")
                
                return True
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
    print("🔬 SIMPLE WORD MCP SERVER TEST")
    print("=" * 50)
    
    success = await test_simple_word_mcp()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ SIMPLE WORD MCP TEST: PASSED")
        print("\n🎯 설정 완료!")
        print("1. Claude Desktop 재시작")
        print("2. 사용 가능한 명령어:")
        print("   - '새 Word 문서를 만들어줘'")
        print("   - 'Word 문서 목록을 보여줘'")
        print("   - '문서에 단락을 추가해줘'")
        print(f"3. 문서 저장 위치: /Users/minyeop/alphagenome/bio-mcp-blast/WordDocuments/")
    else:
        print("❌ SIMPLE WORD MCP TEST: FAILED")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)