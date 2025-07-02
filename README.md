# NCBI Database MCP

🔍 **MCP server for NCBI bioinformatics tools and disease-focused gene expression research**

Enable AI assistants to discover gene expression datasets by disease/condition and access comprehensive NCBI databases through natural language. Perfect for researchers studying disease mechanisms and therapeutic targets.

## 🧬 Features

- **🔬 Disease-Focused GEO Search** - Discover gene expression datasets by disease/condition and organism
- **📊 Comprehensive Study Metadata** - Get detailed methodology, platform, and sample information
- **🧬 Gene-to-Genomic Conversion** - Convert gene names to genomic DNA sequences
- **🐭 Multi-Species Support** - Human, mouse, and rat datasets
- **📈 Research Methodology Details** - RNA-Seq, microarray, ChIP-Seq, and other techniques
- **🔗 Direct Database Links** - Easy access to full datasets and original studies

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

### 🔬 Disease Expression Research (Primary Use Case)
```
User: "Find gene expression datasets for Alzheimer's disease in humans"
AI: [calls search_geo_datasets] → 
📊 Returns 10 datasets with:
- Study methodology (RNA-Seq, Microarray)
- Sample sizes and experimental design
- Platform information (Illumina, Affymetrix)
- Research summaries and direct GEO links
```

```
User: "Show me cancer expression studies in mice using RNA sequencing"
AI: [calls search_geo_datasets] → 
🧪 Filtered results showing:
- RNA-Seq datasets only
- Mouse-specific cancer studies
- Detailed experimental protocols
```

### 🧬 Gene-to-Genomic Analysis
```
User: "Get the genomic sequence for BRCA1"
AI: [calls gene_to_genomic_sequence] → Returns genomic DNA sequence in FASTA format
```

### 📍 Gene Information & Location
```
User: "Find information about TP53 gene"
AI: [calls search_gene_info] → Returns gene location, function, and coordinates
```

### 🎯 Coordinate-Based Sequence Retrieval
```
User: "Get sequence from chr17:43044295-43125483"
AI: [calls get_genomic_sequence] → Returns DNA sequence for specified coordinates
```

## 🛠️ Available Tools

### 🔬 `search_geo_datasets` (Primary Tool)
**Discover gene expression datasets by disease/condition and organism**

**Parameters:**
- `disease` (required) - Disease or condition name
  - Examples: "cancer", "diabetes", "Alzheimer", "heart disease", "depression"
- `organism` - Target organism (default: "Homo sapiens")
  - Options: "Homo sapiens", "Mus musculus", "Rattus norvegicus"
- `study_type` - Expression study methodology (optional)
  - Options: "Expression profiling by array", "Expression profiling by high throughput sequencing"
- `max_results` - Maximum results to return (1-50, default: 10)

**Detailed Output:**
- **📊 Dataset Information**: GDS accession numbers and titles
- **🔬 Study Methodology**: 
  - RNA-Seq (High-throughput transcriptome sequencing)
  - Microarray (Hybridization-based gene expression)
  - ChIP-Seq (Chromatin immunoprecipitation sequencing)
  - SAGE (Serial analysis of gene expression)
- **🧪 Platform Details**: Illumina, Affymetrix, Agilent technologies
- **📈 Experimental Design**: Sample counts, tissue types, treatment conditions
- **📝 Research Context**: Study summaries and disease relevance
- **🔗 Direct Access**: Links to full datasets on NCBI GEO

### 🧬 `gene_to_genomic_sequence`
Convert gene name to genomic DNA sequence

**Parameters:**
- `gene_name` (required) - Gene symbol (e.g., "BRCA1", "TP53")
- `organism` - Target organism (default: "human")
- `sequence_type` - "genomic", "cds", "mrna", "protein"
- `output_format` - "fasta", "genbank", "json"

### 📍 `search_gene_info`
Search for gene information and genomic location

**Parameters:**
- `gene_name` (required) - Gene symbol or name
- `organism` - Target organism (default: "human")

### 🎯 `get_genomic_sequence`
Get genomic sequence from chromosome coordinates

**Parameters:**
- `chromosome` (required) - Chromosome accession (e.g., "NC_000017.11")
- `start` (required) - Start position
- `end` (required) - End position
- `output_format` - "fasta", "json"

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

### 🔬 GEO Dataset Search Optimization
- **Use specific disease terms**: "lung cancer" > "cancer", "type 2 diabetes" > "diabetes"
- **Combine with study types**: Filter by methodology for targeted results
- **Start with small result sets**: Use max_results=5-10 for initial exploration
- **Organism specificity**: Use exact names ("Homo sapiens" not "human")


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

- **[Gene Database](https://www.ncbi.nlm.nih.gov/gene)**
- **[BLAST Documentation](https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Web&PAGE_TYPE=BlastDocs)**


## 🆘 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/hpend2373/NCBI-Database-MCP/issues)
- 💡 **Feature Requests**: [GitHub Issues](https://github.com/hpend2373/NCBI-Database-MCP/issues/new)
- 📖 **Documentation**: [README.md](README.md)

---

*Happy genomics research! 🧬🔍*
