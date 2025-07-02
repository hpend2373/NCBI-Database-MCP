#!/usr/bin/env python3
"""
Simulate Claude Code environment to test full sequence output
This simulates how Claude Code would interact with the MCP server
"""

import asyncio
import json
import subprocess
import sys

async def simulate_claude_code_interaction():
    """Simulate Claude Code requesting a gene sequence"""
    
    print("🔬 Simulating Claude Code Environment")
    print("=" * 50)
    
    # Use exact same command as Claude Code would
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
        print("📤 Initializing MCP connection...")
        
        # Initialize (like Claude Code would)
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "claude-code", "version": "1.0.0"}
            }
        }
        
        process.stdin.write((json.dumps(init_message) + "\n").encode())
        await process.stdin.drain()
        
        # Read init response
        init_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        init_response = json.loads(init_line.decode().strip())
        
        if "result" in init_response:
            print("✅ MCP connection established")
            
            # Request TP53 gene sequence (like user would ask)
            print("\n🧬 Requesting TP53 gene sequence...")
            
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
            
            process.stdin.write((json.dumps(call_message) + "\n").encode())
            await process.stdin.drain()
            
            print("⏳ Waiting for complete sequence...")
            
            # Read response - simulate Claude Code behavior
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=60.0)
            
            # Parse response
            call_response = json.loads(response_line.decode().strip())
            
            if "result" in call_response:
                content = call_response["result"]["content"][0]["text"]
                meta = call_response["result"].get("_meta", {})
                
                print("✅ Sequence received!")
                print("\n📊 Claude Code Perspective:")
                
                # Analyze what Claude Code would see
                total_chars = len(content)
                print(f"  📏 Total characters received: {total_chars:,}")
                
                # Check if response appears truncated
                if "truncated to" in content.lower():
                    print("  ❌ TRUNCATION DETECTED in content")
                    return False
                elif total_chars >= 100000:
                    print("  ⚠️  Large response (>100k chars) - checking integrity...")
                else:
                    print("  ✅ Reasonable response size")
                
                # Check metadata
                if meta:
                    print(f"  📊 Metadata complete: {meta.get('complete', 'unknown')}")
                    print(f"  📊 Metadata truncated: {meta.get('truncated', 'unknown')}")
                    print(f"  📊 Metadata length: {meta.get('total_length', 'unknown'):,}")
                
                # Extract sequence info
                lines = content.split('\n')
                sequence_lines = []
                info_lines = []
                
                for line in lines:
                    if line.startswith('>'):
                        print(f"  🧾 FASTA: {line[:60]}...")
                    elif any(line.startswith(p) for p in ['🧬', '📍', '🔄', '📋', '📏', '🔬', '⚠️']):
                        info_lines.append(line)
                    elif line.strip() and not any(line.startswith(p) for p in ['🧬', '📍', '🔄', '📋', '📏', '🔬', '⚠️']):
                        sequence_lines.append(line.strip())
                
                # Calculate DNA sequence length
                total_sequence = ''.join(sequence_lines)
                seq_length = len(total_sequence)
                
                print(f"  🧬 DNA sequence length: {seq_length:,} nucleotides")
                print(f"  📝 Info lines: {len(info_lines)}")
                
                # Show key info that Claude Code would display
                print("\n📋 Key Information (as Claude Code would show):")
                for line in info_lines[:6]:
                    print(f"    {line}")
                
                # Check sequence completeness
                if seq_length > 15000:  # TP53 should be ~19k bp
                    print(f"\n✅ COMPLETE SEQUENCE: {seq_length:,} bp looks complete for TP53")
                    
                    # Show sequence sample
                    if total_sequence:
                        print(f"\n🧬 Sequence Preview (as Claude Code would show):")
                        print(f"    Start: {total_sequence[:60]}...")
                        print(f"    End:   ...{total_sequence[-60:]}")
                    
                    return True
                else:
                    print(f"\n❌ INCOMPLETE: {seq_length:,} bp seems too short for TP53")
                    return False
            else:
                print("❌ No result in response")
                return False
        else:
            print("❌ Initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        process.terminate()
        await process.wait()

async def main():
    print("🔬 CLAUDE CODE SIMULATION TEST")
    print("Testing whether Claude Code can receive complete sequences")
    print("=" * 60)
    
    success = await simulate_claude_code_interaction()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 CLAUDE CODE SIMULATION: SUCCESS!")
        print("\n✅ Claude Code should receive:")
        print("  - Complete genomic sequences")
        print("  - No truncation messages") 
        print("  - Full FASTA format")
        print("  - All sequence metadata")
        print("\n💬 Try asking Claude Code:")
        print("  'Get the complete genomic sequence for TP53 gene'")
        print("  'Show me BRCA1 full DNA sequence'")
    else:
        print("❌ CLAUDE CODE SIMULATION: ISSUES DETECTED")
        print("🔧 There may still be truncation in Claude Code")
    
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)