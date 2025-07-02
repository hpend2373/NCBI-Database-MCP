#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import { writeFileSync, unlinkSync, existsSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { cpus } from "os";

class HighPerformanceBlastServer {
  constructor() {
    this.server = new Server(
      {
        name: "bio-blast-hpc",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Performance configuration
    this.numThreads = process.env.BLAST_NUM_THREADS || Math.min(8, cpus().length);
    this.blastDbPath = process.env.BLASTDB || join(process.env.HOME || '/tmp', 'blast-databases');
    
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
            name: "blast_local",
            description: "High-performance local BLAST search with optimizations",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Query sequence (FASTA format or raw sequence)",
                },
                program: {
                  type: "string",
                  description: "BLAST program",
                  enum: ["blastn", "blastp", "blastx", "tblastn", "tblastx"],
                  default: "blastn",
                },
                database: {
                  type: "string",
                  description: "Local database name",
                  default: "nt",
                },
                evalue: {
                  type: "number",
                  description: "E-value threshold",
                  default: 10,
                },
                max_hits: {
                  type: "integer",
                  description: "Maximum hits to return",
                  default: 10,
                },
                word_size: {
                  type: "integer",
                  description: "Word size for initial matches (optimization)",
                  minimum: 4,
                },
                num_threads: {
                  type: "integer",
                  description: "Number of CPU threads to use",
                  default: this.numThreads,
                  maximum: cpus().length,
                },
              },
              required: ["query"],
            },
          },
          {
            name: "makeblastdb",
            description: "Create optimized BLAST database from FASTA file",
            inputSchema: {
              type: "object",
              properties: {
                input_file: {
                  type: "string",
                  description: "Path to input FASTA file",
                },
                dbtype: {
                  type: "string",
                  description: "Database type",
                  enum: ["nucl", "prot"],
                  default: "nucl",
                },
                title: {
                  type: "string",
                  description: "Database title",
                },
                parse_seqids: {
                  type: "boolean",
                  description: "Parse sequence IDs",
                  default: true,
                },
              },
              required: ["input_file"],
            },
          },
          {
            name: "list_databases",
            description: "List available local BLAST databases",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "download_database",
            description: "Download NCBI database for local use",
            inputSchema: {
              type: "object",
              properties: {
                database: {
                  type: "string",
                  description: "Database to download",
                  enum: ["16S_ribosomal_RNA", "ITS_RefSeq_Fungi", "refseq_protein", "landmark", "pataa", "patnt"],
                },
                decompress: {
                  type: "boolean",
                  description: "Decompress after download",
                  default: true,
                },
              },
              required: ["database"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "blast_local":
            return {
              content: [{ type: "text", text: await this.runLocalBlast(args) }],
            };
          case "makeblastdb":
            return {
              content: [{ type: "text", text: await this.makeBlastDb(args) }],
            };
          case "list_databases":
            return {
              content: [{ type: "text", text: await this.listDatabases() }],
            };
          case "download_database":
            return {
              content: [{ type: "text", text: await this.downloadDatabase(args) }],
            };
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [{ type: "text", text: `❌ Error: ${error.message}` }],
        };
      }
    });
  }

  async runLocalBlast(args) {
    const {
      query,
      program = "blastn",
      database = "nt",
      evalue = 10,
      max_hits = 10,
      word_size,
      num_threads = this.numThreads,
    } = args;

    // Create temporary file for query
    const queryFile = join(tmpdir(), `blast_query_${Date.now()}.fasta`);
    
    try {
      // Write query to temporary file
      const fastaContent = query.trim().startsWith('>') ? query : `>query\n${query}`;
      writeFileSync(queryFile, fastaContent);

      // Build optimized BLAST command
      const cmd = [
        program,
        "-query", queryFile,
        "-db", database,
        "-evalue", evalue.toString(),
        "-max_target_seqs", max_hits.toString(),
        "-num_threads", num_threads.toString(),
        "-outfmt", "6 qaccver saccver pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle",
      ];

      // Add performance optimizations
      if (word_size) {
        cmd.push("-word_size", word_size.toString());
      }

      // Add program-specific optimizations
      if (program === "blastn") {
        cmd.push("-dust", "yes"); // Low complexity filtering
        cmd.push("-soft_masking", "true"); // Soft masking
      } else if (program === "blastp") {
        cmd.push("-seg", "yes"); // Low complexity filtering for proteins
      }

      console.error(`Running ${program} with ${num_threads} threads...`);
      const result = await this.runCommand(cmd);
      
      if (!result.stdout.trim()) {
        return `✅ High-performance BLAST ${program.toUpperCase()} completed - No significant hits found`;
      }

      // Format results with performance info
      const lines = result.stdout.trim().split('\n');
      let formatted = `✅ High-Performance BLAST ${program.toUpperCase()} Results\n`;
      formatted += `Database: ${database} | Threads: ${num_threads} | E-value: ${evalue}\n`;
      formatted += "=".repeat(60) + "\n\n";

      lines.slice(0, max_hits).forEach((line, i) => {
        const fields = line.split('\t');
        if (fields.length >= 13) {
          formatted += `Hit ${i + 1}:\n`;
          formatted += `  Subject: ${fields[1]}\n`;
          formatted += `  Description: ${fields[12]}\n`;
          formatted += `  Identity: ${fields[2]}%\n`;
          formatted += `  E-value: ${fields[10]}\n`;
          formatted += `  Bit score: ${fields[11]}\n`;
          formatted += `  Alignment length: ${fields[3]}\n`;
          formatted += `  Query: ${fields[6]}-${fields[7]} | Subject: ${fields[8]}-${fields[9]}\n\n`;
        }
      });

      return formatted;

    } catch (error) {
      if (error.code === 'ENOENT') {
        return `❌ ${program} command not found. Please ensure BLAST+ is installed.`;
      }
      if (error.message.includes('Database') || error.message.includes('No such file')) {
        return `❌ Database '${database}' not found. Available databases:\n${await this.listDatabases()}`;
      }
      throw error;
    } finally {
      try {
        unlinkSync(queryFile);
      } catch (e) {}
    }
  }

  async makeBlastDb(args) {
    const { input_file, dbtype = "nucl", title, parse_seqids = true } = args;

    if (!existsSync(input_file)) {
      return `❌ Input file not found: ${input_file}`;
    }

    const dbName = title || input_file.replace(/\.[^/.]+$/, "");
    const cmd = [
      "makeblastdb",
      "-in", input_file,
      "-dbtype", dbtype,
      "-out", join(this.blastDbPath, dbName),
    ];

    if (title) {
      cmd.push("-title", title);
    }

    if (parse_seqids) {
      cmd.push("-parse_seqids");
    }

    try {
      console.error(`Creating BLAST database: ${dbName}`);
      await this.runCommand(cmd);
      return `✅ Successfully created BLAST database: ${dbName}`;
    } catch (error) {
      return `❌ Failed to create database: ${error.message}`;
    }
  }

  async listDatabases() {
    try {
      const cmd = ["blastdbcmd", "-list", this.blastDbPath];
      const result = await this.runCommand(cmd);
      
      if (!result.stdout.trim()) {
        return `📁 No databases found in: ${this.blastDbPath}\n\nTo download databases, use the download_database tool.`;
      }

      return `📁 Available BLAST Databases in ${this.blastDbPath}:\n\n${result.stdout}`;
    } catch (error) {
      return `❌ Error listing databases: ${error.message}`;
    }
  }

  async downloadDatabase(args) {
    const { database, decompress = true } = args;

    const cmd = ["update_blastdb.pl"];
    if (decompress) {
      cmd.push("--decompress");
    }
    cmd.push(database);

    try {
      console.error(`Downloading ${database} database...`);
      const result = await this.runCommand(cmd, { cwd: this.blastDbPath });
      return `✅ Successfully downloaded database: ${database}`;
    } catch (error) {
      return `❌ Failed to download database: ${error.message}`;
    }
  }

  runCommand(cmd, options = {}) {
    return new Promise((resolve, reject) => {
      const process = spawn(cmd[0], cmd.slice(1), {
        stdio: ['ignore', 'pipe', 'pipe'],
        ...options,
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
        reject(new Error('Command timed out'));
      }, 600000); // 10 minutes

      process.on('close', (code) => {
        clearTimeout(timeout);
        if (code !== 0) {
          reject(new Error(stderr || `Command failed with code ${code}`));
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
    console.error(`High-Performance BLAST MCP server running (${this.numThreads} threads)`);
  }
}

const server = new HighPerformanceBlastServer();
server.run().catch(console.error);