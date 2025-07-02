#!/usr/bin/env python3
"""Test GEO Datasets search functionality"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.gene_server_v2 import GeneToGenomicServer

async def test_geo_search():
    """Test GEO datasets search functionality"""
    print("🧬 Testing GEO Datasets Search Functionality")
    print("=" * 60)
    
    server = GeneToGenomicServer()
    
    # Test 1: Cancer datasets
    print("🔍 Test 1: Searching for cancer datasets...")
    
    cancer_args = {
        "query": "cancer",
        "organism": "human",
        "max_results": 5
    }
    
    try:
        cancer_result = await server.search_geo_datasets(cancer_args)
        
        print("✅ Cancer search completed!")
        print("\n📊 Results Preview:")
        
        # Show first few lines
        lines = cancer_result.split('\n')
        for line in lines[:15]:
            if line.strip():
                print(f"  {line}")
        
        if len(lines) > 15:
            print("  ... (results continue)")
        
        # Check for key indicators
        if "Expression profiling by high throughput sequencing" in cancer_result:
            print("✅ Study type filter working")
        
        if "Dataset #" in cancer_result:
            print("✅ Multiple datasets found")
        
        if "Single-cell" in cancer_result or "Bulk" in cancer_result:
            print("✅ Data type detection working")
        
        if "GEO Link:" in cancer_result:
            print("✅ GEO links included")
        
    except Exception as e:
        print(f"❌ Cancer search failed: {e}")
        return False
    
    # Test 2: Brain datasets
    print(f"\n{'='*60}")
    print("🧠 Test 2: Searching for brain datasets...")
    
    brain_args = {
        "query": "brain",
        "organism": "human",
        "max_results": 3
    }
    
    try:
        brain_result = await server.search_geo_datasets(brain_args)
        
        print("✅ Brain search completed!")
        
        # Count datasets found
        dataset_count = brain_result.count("Dataset #")
        print(f"📊 Found {dataset_count} brain datasets")
        
        # Check for tissue-specific results
        if "brain" in brain_result.lower():
            print("✅ Brain-related results found")
        
    except Exception as e:
        print(f"❌ Brain search failed: {e}")
        return False
    
    # Test 3: Single-cell specific search
    print(f"\n{'='*60}")
    print("🔬 Test 3: Searching for single-cell datasets...")
    
    sc_args = {
        "query": "single cell",
        "organism": "human", 
        "max_results": 3
    }
    
    try:
        sc_result = await server.search_geo_datasets(sc_args)
        
        print("✅ Single-cell search completed!")
        
        # Check for single-cell indicators
        if "Single-cell RNA-seq" in sc_result:
            print("✅ Single-cell data type detected")
        
        # Show sample result
        lines = sc_result.split('\n')
        for line in lines[:10]:
            if line.strip() and any(keyword in line for keyword in ['Title:', 'Data Type:', 'Sample Count:']):
                print(f"  {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Single-cell search failed: {e}")
        return False

async def test_geo_mcp_integration():
    """Test GEO search through MCP protocol"""
    print(f"\n{'='*60}")
    print("🔌 Testing GEO Search MCP Integration")
    print("=" * 60)
    
    import json
    import subprocess
    
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
                "clientInfo": {"name": "geo-test", "version": "1.0.0"}
            }
        }
        
        process.stdin.write((json.dumps(init_message) + "\n").encode())
        await process.stdin.drain()
        
        # Read init response
        init_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        init_response = json.loads(init_line.decode().strip())
        
        if "result" in init_response:
            # Check if both tools are available
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
                tool_names = [tool["name"] for tool in tools]
                
                print(f"📋 Available tools: {tool_names}")
                
                if "search_geo_datasets" in tool_names:
                    print("✅ GEO search tool available")
                    
                    # Test GEO search
                    geo_message = {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "search_geo_datasets",
                            "arguments": {
                                "query": "diabetes",
                                "organism": "human",
                                "max_results": 2
                            }
                        }
                    }
                    
                    print("📤 Testing diabetes datasets search...")
                    process.stdin.write((json.dumps(geo_message) + "\n").encode())
                    await process.stdin.drain()
                    
                    geo_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
                    geo_response = json.loads(geo_line.decode().strip())
                    
                    if "result" in geo_response:
                        content = geo_response["result"]["content"][0]["text"]
                        print("✅ GEO search through MCP successful!")
                        
                        # Show summary
                        lines = content.split('\n')[:8]
                        for line in lines:
                            if line.strip():
                                print(f"  {line}")
                        
                        return True
                    else:
                        print("❌ No result in GEO response")
                        return False
                else:
                    print("❌ GEO search tool not found")
                    return False
            else:
                print("❌ Tools list failed")
                return False
        else:
            print("❌ Initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ MCP integration test failed: {e}")
        return False
    finally:
        process.terminate()
        await process.wait()

async def main():
    print("🧬 GEO DATASETS SEARCH TEST SUITE")
    print("=" * 60)
    
    # Test 1: Direct function calls
    test1_success = await test_geo_search()
    
    # Test 2: MCP integration
    test2_success = await test_geo_mcp_integration()
    
    overall_success = test1_success and test2_success
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"  🔬 Direct GEO Search: {'PASSED' if test1_success else 'FAILED'}")
    print(f"  🔌 MCP Integration: {'PASSED' if test2_success else 'FAILED'}")
    print(f"  🎯 Overall: {'PASSED' if overall_success else 'FAILED'}")
    print("=" * 60)
    
    if overall_success:
        print("🎉 GEO Datasets Search Ready!")
        print("\n💬 Usage Examples:")
        print("  - 'Find cancer datasets in GEO'")
        print("  - 'Search for brain RNA-seq studies'")
        print("  - 'Show me single-cell datasets for heart'")
        print("  - 'Find diabetes expression studies'")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)