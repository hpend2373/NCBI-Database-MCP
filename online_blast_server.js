#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

class OnlineBlastServer {
  constructor() {
    this.server = new Server(
      {
        name: "bio-blast-online",
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
            description: "Nucleotide-nucleotide BLAST search using NCBI online service",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Query sequence (DNA/RNA sequence)",
                },
                database: {
                  type: "string",
                  description: "Target database",
                  enum: ["nt", "refseq_rna"],
                  default: "nt",
                },
                max_hits: {
                  type: "integer",
                  description: "Maximum number of hits to return",
                  default: 10,
                  minimum: 1,
                  maximum: 50,
                },
              },
              required: ["query"],
            },
          },
          {
            name: "blastp",
            description: "Protein-protein BLAST search using NCBI online service",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Query sequence (protein sequence)",
                },
                database: {
                  type: "string",
                  description: "Target database",
                  enum: ["nr", "refseq_protein", "swissprot"],
                  default: "nr",
                },
                max_hits: {
                  type: "integer",
                  description: "Maximum number of hits to return",
                  default: 10,
                  minimum: 1,
                  maximum: 50,
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
            const result = await this.runOnlineBlast(name, args);
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

  async runOnlineBlast(program, args) {
    const { query, database = program === "blastn" ? "nt" : "nr", max_hits = 10 } = args;

    try {
      // Clean the sequence - remove any FASTA headers and whitespace
      const cleanQuery = query.replace(/^>.*$/gm, '').replace(/\s/g, '');
      
      if (cleanQuery.length < 10) {
        return "❌ Query sequence too short. Please provide at least 10 nucleotides/amino acids.";
      }

      console.error(`Starting ${program} search against ${database} database...`);

      // Submit BLAST job to NCBI
      const submitUrl = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi";
      const submitParams = new URLSearchParams({
        CMD: "Put",
        PROGRAM: program.toUpperCase(),
        DATABASE: database,
        QUERY: cleanQuery,
        FORMAT_TYPE: "JSON2_S",
        HITLIST_SIZE: max_hits.toString(),
      });

      const submitResponse = await fetch(submitUrl, {
        method: "POST",
        body: submitParams,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      const submitText = await submitResponse.text();
      const ridMatch = submitText.match(/RID = ([A-Z0-9]+)/);
      
      if (!ridMatch) {
        return "❌ Failed to submit BLAST job to NCBI";
      }

      const rid = ridMatch[1];
      console.error(`Job submitted with RID: ${rid}, waiting for completion...`);

      // Poll for results
      let attempts = 0;
      const maxAttempts = 30; // 5 minutes maximum
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds
        attempts++;

        const checkUrl = `https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=Get&FORMAT_OBJECT=SearchInfo&RID=${rid}`;
        const checkResponse = await fetch(checkUrl);
        const checkText = await checkResponse.text();

        if (checkText.includes("Status=READY")) {
          console.error("Job completed, retrieving results...");
          break;
        } else if (checkText.includes("Status=FAILED")) {
          return "❌ BLAST job failed on NCBI server";
        }
        
        if (attempts >= maxAttempts) {
          return "❌ BLAST job timed out. Please try with a shorter sequence.";
        }
      }

      // Get results
      const resultUrl = `https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=Get&FORMAT_TYPE=JSON2_S&RID=${rid}`;
      const resultResponse = await fetch(resultUrl);
      const resultData = await resultResponse.json();

      return this.formatBlastResults(program, database, resultData);

    } catch (error) {
      console.error("BLAST error:", error);
      return `❌ BLAST search failed: ${error.message}`;
    }
  }

  formatBlastResults(program, database, data) {
    try {
      const report = data.BlastOutput2?.[0]?.report;
      if (!report) {
        return "❌ Invalid BLAST result format";
      }

      const search = report.results?.search;
      if (!search || !search.hits || search.hits.length === 0) {
        return `✅ BLAST ${program.toUpperCase()} search completed - No significant hits found in ${database} database`;
      }

      let formatted = `✅ BLAST ${program.toUpperCase()} Results (Database: ${database})\n`;
      formatted += "=".repeat(50) + "\n\n";

      search.hits.slice(0, 10).forEach((hit, i) => {
        const hsp = hit.hsps?.[0]; // Get best HSP (High-scoring Segment Pair)
        if (hsp) {
          formatted += `Hit ${i + 1}:\n`;
          formatted += `  Accession: ${hit.description?.[0]?.accession || 'N/A'}\n`;
          formatted += `  Description: ${hit.description?.[0]?.title || 'N/A'}\n`;
          formatted += `  Identity: ${Math.round((hsp.identity / hsp.align_len) * 100)}%\n`;
          formatted += `  E-value: ${hsp.evalue}\n`;
          formatted += `  Bit score: ${hsp.bit_score}\n`;
          formatted += `  Alignment length: ${hsp.align_len}\n`;
          formatted += `  Query coverage: ${Math.round(((hsp.query_to - hsp.query_from + 1) / search.query_len) * 100)}%\n\n`;
        }
      });

      return formatted;

    } catch (error) {
      console.error("Format error:", error);
      return "❌ Error formatting BLAST results";
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Bio BLAST Online MCP server running on stdio");
  }
}

const server = new OnlineBlastServer();
server.run().catch(console.error);