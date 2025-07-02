#!/bin/bash
cd /Users/minyeop/alphagenome/bio-mcp-blast
source venv/bin/activate
echo "Starting updated Gene-to-Genomic MCP Server (Complete Sequence Version)..." >&2
python src/gene_server_v2.py