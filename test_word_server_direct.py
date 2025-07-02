#!/usr/bin/env python3
"""Test Word MCP Server directly"""

import os
import sys

# Add the server directory to Python path
sys.path.insert(0, '/Users/minyeop/alphagenome/bio-mcp-blast/Office-Word-MCP-Server')

# Set environment variables
os.environ['DOCUMENT_DIR'] = '/Users/minyeop/alphagenome/bio-mcp-blast/WordDocuments'
os.environ['FASTMCP_LOG_LEVEL'] = 'INFO'
os.environ['MCP_TRANSPORT'] = 'stdio'

# Change to WordDocuments directory
os.chdir('/Users/minyeop/alphagenome/bio-mcp-blast/WordDocuments')

print("Testing Word MCP Server directly...")
print("=" * 50)

try:
    # Import and run the server
    from word_document_server.main import run_server
    
    print("Starting Word Document Server...")
    print("This will start the server in STDIO mode.")
    print("You should see 'Starting MCP server' message if successful.")
    print("Press Ctrl+C to stop.")
    
    run_server()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()