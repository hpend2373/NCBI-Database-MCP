# Use biocontainers BLAST image
FROM biocontainers/blast:2.15.0 AS blast-tools

# Build MCP server layer
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy BLAST binaries from biocontainer
COPY --from=blast-tools /usr/local/bin/blastn /usr/local/bin/
COPY --from=blast-tools /usr/local/bin/blastp /usr/local/bin/
COPY --from=blast-tools /usr/local/bin/makeblastdb /usr/local/bin/
COPY --from=blast-tools /usr/local/bin/blastdbcmd /usr/local/bin/

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .

# Copy server code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 mcp && \
    mkdir -p /tmp/mcp-blast && \
    chown -R mcp:mcp /app /tmp/mcp-blast

USER mcp

# Set environment variables
ENV BIO_MCP_TEMP_DIR=/tmp/mcp-blast
ENV PATH="/usr/local/bin:${PATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import src.server" || exit 1

# Run the server
CMD ["python", "-m", "src.server"]