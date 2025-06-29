# Bio-MCP BLAST

🔍 **MCP server for NCBI BLAST sequence similarity search**

Enable AI assistants to perform BLAST searches through natural language. Search nucleotide and protein databases, create custom databases, and get formatted results instantly.

## 🧬 Features

- **blastn** - Nucleotide-nucleotide BLAST search
- **blastp** - Protein-protein BLAST search  
- **makeblastdb** - Create custom BLAST databases
- **Multiple output formats** - JSON, XML, tabular, pairwise
- **Flexible input** - File paths or raw sequences
- **Queue support** - Async processing for large searches

## 🚀 Quick Start

### Installation

```bash
# Install BLAST+
conda install -c bioconda blast

# Or via package manager
# macOS: brew install blast
# Ubuntu: sudo apt-get install ncbi-blast+

# Install MCP server
git clone https://github.com/bio-mcp/bio-mcp-blast.git
cd bio-mcp-blast
pip install -e .
```

### Basic Usage

```bash
# Start the server
python -m src.server

# Or with queue support
python -m src.main --mode queue
```

### Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "bio-blast": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/bio-mcp-blast"
    }
  }
}
```

## 💡 Usage Examples

### Simple Sequence Search
```
User: "BLAST this sequence against nr: ATGCGATCGATCG"
AI: [calls blastn] → Returns top hits with E-values and alignments
```

### File-Based Search
```
User: "Search proteins.fasta against SwissProt database"
AI: [calls blastp] → Processes file and returns similarity results
```

### Database Creation
```
User: "Create a BLAST database from reference_genomes.fasta"
AI: [calls makeblastdb] → Creates searchable database files
```

### Long-Running Search
```
User: "BLAST large_dataset.fasta against nt database"
AI: [calls blastn_async] → "Job submitted! ID: abc123, checking progress..."
```

## 🛠️ Available Tools

### `blastn`
Nucleotide-nucleotide BLAST search

**Parameters:**
- `query` (required) - Path to FASTA file or sequence string
- `database` (required) - Database name (e.g., "nt", "nr") or path
- `evalue` - E-value threshold (default: 10)
- `max_hits` - Maximum hits to return (default: 50)
- `output_format` - Output format: "tabular", "xml", "json", "pairwise"

### `blastp`
Protein-protein BLAST search

**Parameters:**
- Same as blastn, but for protein sequences

### `makeblastdb`
Create BLAST database from FASTA file

**Parameters:**
- `input_file` (required) - Path to FASTA file
- `database_name` (required) - Name for output database
- `dbtype` (required) - "nucl" or "prot"
- `title` - Database title (optional)

### Async Variants (Queue Mode)
- `blastn_async` - Submit nucleotide search to queue
- `blastp_async` - Submit protein search to queue
- `get_job_status` - Check job progress
- `get_job_result` - Retrieve completed results

## ⚙️ Configuration

### Environment Variables

```bash
# Basic settings
export BIO_MCP_MAX_FILE_SIZE=100000000    # 100MB max file size
export BIO_MCP_TIMEOUT=300                # 5 minute timeout
export BIO_MCP_BLAST_PATH="blastn"        # BLAST executable path

# Queue mode settings
export BIO_MCP_QUEUE_URL="http://localhost:8000"
```

### Database Setup

```bash
# Download common databases
mkdir -p ~/blast-databases
cd ~/blast-databases

# NCBI databases (large downloads!)
update_blastdb.pl --decompress nt
update_blastdb.pl --decompress nr
update_blastdb.pl --decompress swissprot

# Set environment variable
export BLASTDB=~/blast-databases
```

## 🐳 Docker Deployment

### Local Docker

```bash
# Build image
docker build -t bio-mcp-blast .

# Run container
docker run -p 5000:5000 \
  -v ~/blast-databases:/data/blast-db:ro \
  -e BLASTDB=/data/blast-db \
  bio-mcp-blast
```

### Docker Compose

```yaml
services:
  blast-server:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./databases:/data/blast-db:ro
    environment:
      - BLASTDB=/data/blast-db
      - BIO_MCP_TIMEOUT=600
```

## 🔄 Queue System

For long-running BLAST searches, use the queue system:

### Setup

```bash
# Start queue infrastructure
cd ../bio-mcp-queue
./setup-local.sh

# Start BLAST server with queue support
python -m src.main --mode queue --queue-url http://localhost:8000
```

### Usage

```python
# Submit async job
job_info = await blast_server.submit_job(
    job_type="blastn",
    parameters={
        "query": "large_sequences.fasta",
        "database": "nt",
        "evalue": 0.001
    }
)

# Check status
status = await blast_server.get_job_status(job_info["job_id"])

# Get results when complete
results = await blast_server.get_job_result(job_info["job_id"])
```

## 📊 Output Formats

### Tabular (Default)
```
# Fields: query_id, subject_id, percent_identity, alignment_length, ...
Query_1    gi|123456    98.5    500    7    0    1    500    1000    1499    1e-180    633
```

### JSON
```json
{
  "BlastOutput2": [{
    "report": {
      "results": {
        "search": {
          "query_title": "Query_1",
          "hits": [...]
        }
      }
    }
  }]
}
```

### XML
Standard BLAST XML format for programmatic parsing.

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Test with real data
python tests/test_integration.py

# Performance testing
python tests/benchmark.py
```

## 📈 Performance Tips

### Local Optimization
- Use SSD storage for databases
- Increase available RAM
- Use multiple CPU cores: `export BLAST_NUM_THREADS=8`

### Database Selection
- Use smaller, specific databases when possible
- Consider pre-filtering sequences
- Use appropriate E-value thresholds

### Queue Optimization
- Scale workers based on CPU cores
- Use separate queues for different database sizes
- Monitor memory usage with large databases

## 🔐 Security

### Input Validation
- File size limits prevent resource exhaustion
- Path validation prevents directory traversal
- Command injection protection

### Sandboxing
- Containers run as non-root user
- Temporary files isolated per job
- Network access restricted in production

## 🐛 Troubleshooting

### Common Issues

**BLAST not found**
```bash
# Check installation
which blastn
blastn -version

# Install via conda
conda install -c bioconda blast
```

**Database not found**
```bash
# Check BLASTDB environment variable
echo $BLASTDB

# List available databases
blastdbcmd -list /path/to/databases
```

**Out of memory**
```bash
# Reduce max_target_seqs
blastn -max_target_seqs 100

# Use streaming for large outputs
# Increase system swap space
```

**Timeout errors**
```bash
# Increase timeout
export BIO_MCP_TIMEOUT=3600  # 1 hour

# Or use queue mode for long searches
python -m src.main --mode queue
```

## 📚 Resources

- **[BLAST Documentation](https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Web&PAGE_TYPE=BlastDocs)**
- **[BLAST Databases](https://ftp.ncbi.nlm.nih.gov/blast/db/)**
- **[Bio-MCP Examples](https://github.com/bio-mcp/bio-mcp-examples)**
- **[Queue System Setup](https://github.com/bio-mcp/bio-mcp-queue)**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🆘 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/bio-mcp/bio-mcp-blast/issues)
- 💡 **Feature Requests**: [GitHub Issues](https://github.com/bio-mcp/bio-mcp-blast/issues/new?template=feature_request.md)
- 📖 **Documentation**: [Bio-MCP Docs](https://github.com/bio-mcp/bio-mcp-docs)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/bio-mcp/bio-mcp-blast/discussions)

---

*Happy BLASTing! 🧬🔍*