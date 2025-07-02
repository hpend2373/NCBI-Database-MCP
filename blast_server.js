#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import { writeFileSync, unlinkSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

class BlastServer {
  constructor() {
    this.server = new Server(
      {
        name: "bio-blast-mcp",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error("[MCP Error]", error);
    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "blastn",
            description: "Nucleotide-nucleotide BLAST search",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Query sequence (FASTA format or raw sequence)",
                },
                database: {
                  type: "string",
                  description: "Target database name (e.g., 'nt', 'nr')",
                  default: "nt",
                },
                evalue: {
                  type: "number",
                  description: "E-value threshold",
                  default: 10,
                },
                max_hits: {
                  type: "integer",
                  description: "Maximum number of hits to return",
                  default: 10,
                },
              },
              required: ["query"],
            },
          },
          {
            name: "blastp",
            description: "Protein-protein BLAST search",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Query sequence (FASTA format or raw sequence)",
                },
                database: {
                  type: "string",
                  description: "Target database name (e.g., 'nr', 'swissprot')",
                  default: "nr",
                },
                evalue: {
                  type: "number",
                  description: "E-value threshold",
                  default: 10,
                },
                max_hits: {
                  type: "integer",
                  description: "Maximum number of hits to return",
                  default: 10,
                },
              },
              required: ["query"],
            },
          },
          {
            name: "echo",
            description: "Echo back the input message for testing",
            inputSchema: {
              type: "object",
              properties: {
                message: {
                  type: "string",
                  description: "Message to echo back",
                },
              },
              required: ["message"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "echo":
            return {
              content: [
                {
                  type: "text",
                  text: `✅ Echo: ${args.message}`,
                },
              ],
            };

          case "blastn":
          case "blastp":
            const result = await this.runBlast(name, args);
            return {
              content: [
                {
                  type: "text",
                  text: result,
                },
              ],
            };

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `❌ Error: ${error.message}`,
            },
          ],
        };
      }
    });
  }

  async runBlast(blastType, args) {
    const { query, database = blastType === "blastn" ? "nt" : "nr", evalue = 10, max_hits = 10 } = args;

    // Create temporary file for query
    const queryFile = join(tmpdir(), `blast_query_${Date.now()}.fasta`);
    
    try {
      // Write query to temporary file
      const fastaContent = query.trim().startsWith('>') ? query : `>query\n${query}`;
      writeFileSync(queryFile, fastaContent);

      // Build BLAST command
      const cmd = [
        blastType,
        "-query", queryFile,
        "-db", database,
        "-evalue", evalue.toString(),
        "-max_target_seqs", max_hits.toString(),
        "-outfmt", "6 qaccver saccver pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle"
      ];

      // Run BLAST
      const result = await this.runCommand(cmd);
      
      if (!result.stdout.trim()) {
        return `✅ BLAST ${blastType.toUpperCase()} search completed - No significant hits found for query in ${database} database`;
      }

      // Format results
      const lines = result.stdout.trim().split('\n');
      let formatted = `✅ BLAST ${blastType.toUpperCase()} Results (Database: ${database})\n`;
      formatted += "=".repeat(50) + "\n\n";

      lines.slice(0, max_hits).forEach((line, i) => {
        const fields = line.split('\t');
        if (fields.length >= 13) {
          formatted += `Hit ${i + 1}:\n`;
          formatted += `  Subject: ${fields[1]}\n`;
          formatted += `  Description: ${fields[12]}\n`;
          formatted += `  Identity: ${fields[2]}%\n`;
          formatted += `  E-value: ${fields[10]}\n`;
          formatted += `  Bit score: ${fields[11]}\n`;
          formatted += `  Alignment length: ${fields[3]}\n\n`;
        }
      });

      return formatted;

    } catch (error) {
      if (error.code === 'ENOENT') {
        return `❌ ${blastType} command not found. Please ensure BLAST+ is installed and in PATH`;
      }
      throw error;
    } finally {
      // Clean up temporary file
      try {
        unlinkSync(queryFile);
      } catch (e) {
        // Ignore cleanup errors
      }
    }
  }

  runCommand(cmd) {
    return new Promise((resolve, reject) => {
      const process = spawn(cmd[0], cmd.slice(1), {
        stdio: ['ignore', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      const timeout = setTimeout(() => {
        process.kill();
        reject(new Error('BLAST search timed out after 5 minutes'));
      }, 300000); // 5 minutes

      process.on('close', (code) => {
        clearTimeout(timeout);
        if (code !== 0) {
          reject(new Error(`BLAST failed: ${stderr}`));
        } else {
          resolve({ stdout, stderr });
        }
      });

      process.on('error', (error) => {
        clearTimeout(timeout);
        reject(error);
      });
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Bio BLAST MCP server running on stdio");
  }
}

const server = new BlastServer();
server.run().catch(console.error);