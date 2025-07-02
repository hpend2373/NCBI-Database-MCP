# NCBI Database MCP

🔍 **MCP server for NCBI bioinformatics tools and database access**

Enable AI assistants to perform gene searches, BLAST analysis, and genomic sequence retrieval through natural language. Access NCBI databases including Gene, PubMed, and BLAST services.

## 🧬 Features

- **Gene-to-Genomic Conversion** - Convert gene names to genomic DNA sequences
- **GEO Dataset Search** - Find gene expression datasets by disease and organism
- **NCBI Database Access** - Gene, GEO, and sequence databases
- **Multiple Output Formats** - FASTA, GenBank, JSON
- **Disease-Focused Research** - Search expression studies by condition
- **Multiple Organisms** - Human, mouse, and other model organisms

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/hpend2373/NCBI-Database-MCP.git
cd NCBI-Database-MCP

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Start the FastMCP server (recommended)
./run_fastmcp_gene_server.sh

# Or start the standard MCP server
python src/gene_to_genomic_server.py
```

### Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "ncbi-database": {
      "command": "python",
      "args": ["src/gene_to_genomic_server.py"],
      "cwd": "/path/to/NCBI-Database-MCP",
      "env": {
        "NCBI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Alternative: Set global environment variable**
```bash
export NCBI_API_KEY="your_api_key_here"
```

Then use simpler config:
```json
{
  "mcpServers": {
    "ncbi-database": {
      "command": "python",
      "args": ["src/gene_to_genomic_server.py"],
      "cwd": "/path/to/NCBI-Database-MCP"
    }
  }
}
```

## 💡 Usage Examples

### Gene to Genomic Sequence
```
User: "Get the genomic sequence for BRCA1"
AI: [calls gene_to_genomic_sequence] → Returns genomic DNA sequence in FASTA format
```

### Gene Information Search
```
User: "Find information about TP53 gene"
AI: [calls search_gene_info] → Returns gene location, function, and coordinates
```

### Coordinate-Based Sequence
```
User: "Get sequence from chr17:43044295-43125483"
AI: [calls get_genomic_sequence] → Returns DNA sequence for specified coordinates
```

### Disease Expression Datasets
```
User: "Find gene expression datasets for diabetes in mice"
AI: [calls search_geo_datasets] → Returns GEO datasets with study details and methodology
```

## 🛠️ Available Tools

### `gene_to_genomic_sequence`
Convert gene name to genomic DNA sequence

**Parameters:**
- `gene_name` (required) - Gene symbol or name
- `organism` - Target organism (default: "human")
- `sequence_type` - "genomic", "cds", "mrna", "protein"
- `output_format` - "fasta", "genbank", "json"

### `search_gene_info`
Search for gene information and genomic location

**Parameters:**
- `gene_name` (required) - Gene symbol or name
- `organism` - Target organism (default: "human")

### `get_genomic_sequence`
Get genomic sequence from chromosome coordinates

**Parameters:**
- `chromosome` (required) - Chromosome number/name
- `start` (required) - Start position
- `end` (required) - End position
- `organism` - Target organism (default: "human")

### `search_geo_datasets`
Search GEO datasets by disease/condition and organism

**Parameters:**
- `disease` (required) - Disease or condition name (e.g., "cancer", "diabetes", "Alzheimer")
- `organism` - Target organism ("Homo sapiens", "Mus musculus", "Rattus norvegicus")
- `study_type` - Expression study type (array, sequencing, etc.)
- `max_results` - Maximum results to return (1-50, default: 10)

**Returns:**
- Dataset ID and accession numbers
- Study methodology and platform information
- Sample counts and experimental design
- Research summaries and direct links

## ⚙️ Configuration

### Environment Variables

You can configure the server using environment variables:

```bash
# Copy example file and edit
cp .env.example .env

# Or set directly
export NCBI_API_KEY="your_api_key_here"

# Get your free API key from: https://www.ncbi.nlm.nih.gov/account/
# Without API key: 3 requests/second
# With API key: 10 requests/second
```

## 📁 Project Structure

```
NCBI-Database-MCP/
├── README.md                    # Documentation
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── .env.example                # Environment variables template
├── run_fastmcp_gene_server.sh  # Launch script
└── src/
    ├── gene_to_genomic_server.py  # Standard MCP server
    └── fastmcp_gene_server.py     # FastMCP server (recommended)
```

## 📈 Performance Tips

- Get NCBI API key for higher rate limits (10 req/sec vs 3 req/sec)
- Use specific disease terms for better GEO search results
- Cache results for repeated queries
- Consider organism-specific databases
- Limit GEO search results to avoid large responses

## 🐛 Troubleshooting

### Common Issues

**Gene not found**
```bash
# Check gene name spelling
# Try alternative gene symbols
# Verify organism specification
```

**No GEO datasets found**
```bash
# Try broader disease terms (e.g., "cancer" instead of "lung adenocarcinoma")
# Check organism name (use "Homo sapiens" not "human")
# Try without study_type filter
# Verify disease spelling and terminology
```

**API rate limiting**
```bash
# Get free NCBI API key: https://www.ncbi.nlm.nih.gov/account/
# Set NCBI_API_KEY environment variable
# Without key: 3 requests/second limit
# With key: 10 requests/second limit
```

**Network timeouts**
```bash
# Check internet connection
# Increase timeout values
# Retry failed requests
```

## 📚 Resources

- **[NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)**
- **[Gene Database](https://www.ncbi.nlm.nih.gov/gene)**
- **[BLAST Documentation](https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Web&PAGE_TYPE=BlastDocs)**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🆘 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/hpend2373/NCBI-Database-MCP/issues)
- 💡 **Feature Requests**: [GitHub Issues](https://github.com/hpend2373/NCBI-Database-MCP/issues/new)
- 📖 **Documentation**: [README.md](README.md)

---

*Happy genomics research! 🧬🔍*
