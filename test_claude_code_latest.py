#!/usr/bin/env python3
"""Test Claude Code integration with latest version selection"""

import asyncio
import json
import subprocess
import sys

async def test_claude_code_latest_version():
    """Test Claude Code integration with latest version selection"""
    
    print("🔄 Testing Claude Code Integration with Latest Version Selection...")
    
    # Use the exact command from Claude Code configuration
    server_cmd = [
        "/Users/minyeop/alphagenome/bio-mcp-blast/venv/bin/python",
        "src/gene_server_v2.py"
    ]
    
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
        # Initialize
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "claude-code-latest-test", "version": "1.0.0"}
            }
        }
        
        process.stdin.write((json.dumps(init_message) + "\n").encode())
        await process.stdin.drain()
        
        # Read init response
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        init_response = json.loads(response_line.decode().strip())
        
        if "result" in init_response:
            # Test with TP53 gene to verify latest version selection
            call_message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "gene_to_sequence",
                    "arguments": {
                        "gene_name": "TP53",
                        "organism": "human"
                    }
                }
            }
            
            print("📤 Testing gene_to_sequence with TP53 (checking latest version)...")
            process.stdin.write((json.dumps(call_message) + "\n").encode())
            await process.stdin.drain()
            
            call_response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
            call_response = json.loads(call_response_line.decode().strip())
            
            if "result" in call_response:
                content = call_response["result"]["content"][0]["text"]
                
                print("✅ Response received!")
                print("\n📊 Version Information Check:")
                
                # Check for version-related information
                lines = content.split('\n')
                version_found = False
                latest_annotation = False
                
                for line in lines[:15]:  # Check first 15 lines
                    if "Version:" in line:
                        print(f"  🔄 {line}")
                        version_found = True
                        if "RS_2024" in line:
                            latest_annotation = True
                    elif "Annotation:" in line:
                        print(f"  📋 {line}")
                        if "RS_2024" in line:
                            latest_annotation = True
                    elif any(keyword in line for keyword in ['Gene:', 'Location:', 'Length:']):
                        print(f"  📍 {line}")
                
                print("\n🔍 Analysis:")
                if version_found:
                    print("  ✅ Version information is included")
                else:
                    print("  ❌ Version information missing")
                
                if latest_annotation:
                    print("  ✅ Latest annotation (RS_2024_xx) detected")
                else:
                    print("  ❌ Latest annotation not detected")
                
                if "(LATEST VERSION)" in content:
                    print("  ✅ Latest version label found in output")
                else:
                    print("  ❌ Latest version label missing")
                
                success = version_found and latest_annotation
                return success
        
        return False
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    finally:
        process.terminate()
        await process.wait()

async def main():
    print("=" * 70)
    print("🔄 CLAUDE CODE LATEST VERSION INTEGRATION TEST")
    print("=" * 70)
    
    success = await test_claude_code_latest_version()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ CLAUDE CODE LATEST VERSION INTEGRATION: SUCCESS!")
        print("\n🎯 Key Features Now Available in Claude Code:")
        print("  🔄 Automatic latest version selection")
        print("  📋 Latest annotation releases (RS_2024_xx)")
        print("  🏗️ Primary reference assembly (GRCh38)")
        print("  📊 Version information in results")
        print("  🧬 Complete genomic sequences")
        print("\n💬 Usage in Claude Code:")
        print("  - 'Get the latest TP53 genomic sequence'")
        print("  - 'Show me BRCA1 complete DNA sequence'")
        print("  - 'I need the genomic sequence for EGFR gene'")
    else:
        print("❌ CLAUDE CODE LATEST VERSION INTEGRATION: FAILED")
        print("🔧 Please check server configuration")
    
    print("=" * 70)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)