#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

class StableOnlineBlastServer {
  constructor() {
    this.server = new Server(
      {
        name: "bio-blast-stable",
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
            name: "blast_online",
            description: "BLAST search using NCBI online service with retry mechanism",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Query sequence (DNA/RNA or protein)",
                },
                program: {
                  type: "string",
                  description: "BLAST program",
                  enum: ["blastn", "blastp", "blastx", "tblastn"],
                  default: "blastn",
                },
                database: {
                  type: "string",
                  description: "Target database",
                  enum: ["nt", "nr", "refseq_rna", "refseq_protein", "swissprot"],
                  default: "nt",
                },
                max_hits: {
                  type: "integer",
                  description: "Maximum number of hits",
                  default: 5,
                  minimum: 1,
                  maximum: 20,
                },
              },
              required: ["query"],
            },
          },
          {
            name: "demo_blast",
            description: "Demo BLAST with sample sequences (no internet required)",
            inputSchema: {
              type: "object",
              properties: {
                sample: {
                  type: "string",
                  description: "Sample sequence to demonstrate",
                  enum: ["human_insulin", "ecoli_16s", "covid_spike"],
                  default: "human_insulin",
                },
              },
            },
          },
          {
            name: "echo",
            description: "Test connectivity",
            inputSchema: {
              type: "object",
              properties: {
                message: {
                  type: "string",
                  description: "Test message",
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

          case "demo_blast":
            const demoResult = await this.runDemoBlast(args);
            return {
              content: [
                {
                  type: "text",
                  text: demoResult,
                },
              ],
            };

          case "blast_online":
            const result = await this.runOnlineBlastWithRetry(args);
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

  async runDemoBlast(args) {
    const { sample = "human_insulin" } = args;

    const samples = {
      human_insulin: {
        sequence: "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
        type: "protein",
        description: "Human insulin precursor protein",
      },
      ecoli_16s: {
        sequence: "AAATTGAAGAGTTTGATCATGGCTCAGATTGAACGCTGGCGGCAGGCCTAACACATGCAAGTCGAACGGTAACAGGAAGAAGCTTGCTCTTTGCTGACGAGTGGCGGACGGGTGAGTAATGTCTGGGAAACTGCCTGATGGAGGGGGATAACTACTGGAAACGGTAGCTAATACCGCATAACGTCGCAAGACCAAAGAGGGGGACCTTCGGGCCTCTTGCCATCGGATGTGCCCAGATGGGATTAGCTAGTAGGTGGGGTAACGGCTCACCTAGGCGACGATCCCTAGCTGGTCTGAGAGGATGACCAGCCACACTGGAACTGAGACACGGTCCAGACTCCTACGGGAGGCAGCAGTGGGGAATATTGCACAATGGGCGCAAGCCTGATGCAGCCATGCCGCGTGTATGAAGAAGGCCTTCGGGTTGTAAAGTACTTTCAGCGGGGAGGAAGGGAGTAAAGTTAATACCTTTGCTCATTGACGTTACCCGCAGAAGAAGCACCGGCTAACTCCGTGCCAGCAGCCGCGGTAATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGCGCACGCAGGCGGTTTGTTAAGTCAGATGTGAAATCCCCGGGCTCAACCTGGGAACTGCATCTGATACTGGCAAGCTTGAGTCTCGTAGAGGGGGGTAGAATTCCAGGTGTAGCGGTGAAATGCGTAGAGATCTGGAGGAATACCGGTGGCGAAGGCGGCCCCCTGGACGAAGACTGACGCTCAGGTGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGTCGACTTGGAGGTTGTGCCCTTGAGGCGTGGCTTCCGGAGCTAACGCGTTAAGTCGACCGCCTGGGGAGTACGGCCGCAAGGTTAAAACTCAAATGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGATGCAACGCGAAGAACCTTACCTGGTCTTGACATCCACGGAAGTTTTCAGAGATGAGAATGTGCCTTCGGGAACCGTGAGACAGGTGCTGCATGGCTGTCGTCAGCTCGTGTTGTGAAATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTATCCTTTGTTGCCAGCGGTCCGGCCGGGAACTCAAAGGAGACTGCCAGTGATAAACTGGAGGAAGGTGGGGATGACGTCAAGTCATCATGGCCCTTACGACCAGGGCTACACACGTGCTACAATGGCGCATACAAAGAGAAGCGACCTCGCGAGAGCAAGCGGACCTCATAAAGTGCGTCGTAGTCCGGATTGGAGTCTGCAACTCGACTCCATGAAGTCGGAATCGCTAGTAATCGTGGATCAGAATGCCACGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCATGGGAGTGGGTTGCAAAAGAAGTAGGTAGCTTAACCTTCGGGAGGGCGCTTACCACTTTGTGATTCATGACTGGGGTGAAGTCGTAACAAGGTAACCGTAGGGGAACCTGCGGTTGGATCACCTCCTTA",
        type: "dna",
        description: "E. coli 16S ribosomal RNA gene",
      },
      covid_spike: {
        sequence: "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHVSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATNVVIKVCEFQFCNDPFLGVYYHKNNKSWMESEFRVYSSANNCTFEYVSQPFLMDLEGKQGNFKNLREFVFKNIDGYFKIYSKHTPINLVRDLPQGFSALEPLVDLPIGINITRFQTLLALHRSYLTPGDSSSGWTAGAAAYYVGYLQPRTFLLKYNENGTITDAVDCALDPLSETKCTLKSFTVEKGIYQTSNFRVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNFNFNGLTGTGVLTESNKKFLPFQQFGRDIADTTDAVRDPQTLEILDITPCSFGGVSVITPGTNTSNQVAVLYQDVNCTEVPVAIHADQLTPTWRVYSTGSNVFQTRAGCLIGAEHVNNSYECDIPIGAGICASYQTQTNSPRRARSVASQSIIAYTMSLGAENSVAYSNNSIAIPTNFTISVTTEILPVSMTKTSVDCTMYICGDSTECSNLLLQYGSFCTQLNRALTGIAVEQDKNTQEVFAQVKQIYKTPPIKDFGGFNFSQILPDPSKPSKRSFIEDLLFNKVTLADAGFIKQYGDCLGDIAARDLICAQKFNGLTVLPPLLTDEMIAQYTSALLAGTITSGWTFGAGAALQIPFAMQMAYRFNGIGVTQNVLYENQKLIANQFNSAIGKIQDSLSSTASALGKLQDVVNQNAQALNTLVKQLSSNFGAISSVLNDILSRLDKVEAEVQIDRLITGRLQSLQTYVTQQLIRAAEIRASANLAATKMSECVLGQSKRVDFCGKGYHLMSFPQSAPHGVVFLHVTYVPAQEKNFTTAPAICHDGKAHFPREGVFVSNGTHWFVTQRNFYEPQIITTDNTFVSGNCDVVIGIVNNTVYDPLQPELDSFKEELDKYFKNHTSPDVDLGDISGINASVVNIQKEIDRLNEVAKNLNESLIDLQELGKYEQYIKWPWYIWLGFIAGLIAIVMVTIMLCCMTSCCSCLKGCCSCGSCCKFDEDDSEPVLKGVKLHYT",
        type: "protein",
        description: "SARS-CoV-2 spike protein",
      },
    };

    const sampleData = samples[sample];
    if (!sampleData) {
      return "❌ Unknown sample. Available: human_insulin, ecoli_16s, covid_spike";
    }

    return `🧬 Demo BLAST Sample: ${sample.toUpperCase()}

📝 Description: ${sampleData.description}
🔤 Type: ${sampleData.type}
📏 Length: ${sampleData.sequence.length} ${sampleData.type === 'dna' ? 'nucleotides' : 'amino acids'}

🧪 Sequence (first 100 chars):
${sampleData.sequence.substring(0, 100)}...

💡 To search this sequence:
Use blast_online tool with program="${sampleData.type === 'dna' ? 'blastn' : 'blastp'}"

⚠️ Note: This is demo data. For real BLAST search, use the blast_online tool.`;
  }

  async runOnlineBlastWithRetry(args) {
    const maxRetries = 3;
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.error(`BLAST attempt ${attempt}/${maxRetries}...`);
        return await this.runOnlineBlast(args);
      } catch (error) {
        lastError = error;
        console.error(`Attempt ${attempt} failed:`, error.message);
        
        if (attempt < maxRetries) {
          const delay = attempt * 2000; // 2s, 4s delays
          console.error(`Retrying in ${delay/1000} seconds...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    // All attempts failed
    return `❌ BLAST search failed after ${maxRetries} attempts.

Last error: ${lastError.message}

🔧 Troubleshooting suggestions:
1. Check internet connection
2. Try again in a few minutes (NCBI may be busy)
3. Use demo_blast tool to test functionality
4. Consider shorter sequences (< 1000 characters)

💡 Alternative: Use demo_blast tool with sample sequences for testing.`;
  }

  async runOnlineBlast(args) {
    const { 
      query, 
      program = "blastn", 
      database = program === "blastn" ? "nt" : "nr", 
      max_hits = 5 
    } = args;

    // Validate and clean query
    const cleanQuery = query.replace(/^>.*$/gm, '').replace(/\s/g, '');
    
    if (cleanQuery.length < 10) {
      return "❌ Query too short. Minimum 10 characters required.";
    }

    if (cleanQuery.length > 2000) {
      return "❌ Query too long. Maximum 2000 characters for online BLAST.";
    }

    // Use NCBI BLAST API with shorter timeout
    const submitUrl = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi";
    const submitParams = new URLSearchParams({
      CMD: "Put",
      PROGRAM: program.toUpperCase(),
      DATABASE: database,
      QUERY: cleanQuery,
      FORMAT_TYPE: "JSON2_S",
      HITLIST_SIZE: Math.min(max_hits, 10).toString(),
      EXPECT: "10",
    });

    // Submit with timeout
    const submitResponse = await fetch(submitUrl, {
      method: "POST",
      body: submitParams,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "BioBLAST-MCP/1.0",
      },
      timeout: 10000, // 10 second timeout
    });

    if (!submitResponse.ok) {
      throw new Error(`HTTP ${submitResponse.status}: ${submitResponse.statusText}`);
    }

    const submitText = await submitResponse.text();
    const ridMatch = submitText.match(/RID = ([A-Z0-9]+)/);
    
    if (!ridMatch) {
      throw new Error("Failed to get RID from NCBI response");
    }

    const rid = ridMatch[1];
    console.error(`Job submitted: ${rid}`);

    // Poll for results with shorter intervals
    let attempts = 0;
    const maxAttempts = 20; // 3-4 minutes max
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 5000)); // 5 second intervals
      attempts++;

      const checkUrl = `https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=Get&FORMAT_OBJECT=SearchInfo&RID=${rid}`;
      const checkResponse = await fetch(checkUrl, { timeout: 5000 });
      const checkText = await checkResponse.text();

      if (checkText.includes("Status=READY")) {
        console.error("Results ready, fetching...");
        break;
      } else if (checkText.includes("Status=FAILED")) {
        throw new Error("BLAST job failed on server");
      }
      
      if (attempts >= maxAttempts) {
        throw new Error("BLAST job timed out");
      }
    }

    // Get results
    const resultUrl = `https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=Get&FORMAT_TYPE=JSON2_S&RID=${rid}`;
    const resultResponse = await fetch(resultUrl, { timeout: 10000 });
    
    if (!resultResponse.ok) {
      throw new Error(`Failed to fetch results: ${resultResponse.status}`);
    }
    
    const resultData = await resultResponse.json();
    return this.formatBlastResults(program, database, resultData);
  }

  formatBlastResults(program, database, data) {
    try {
      const report = data.BlastOutput2?.[0]?.report;
      if (!report) {
        return "❌ Invalid result format from NCBI";
      }

      const search = report.results?.search;
      if (!search || !search.hits || search.hits.length === 0) {
        return `✅ BLAST ${program.toUpperCase()} completed - No significant hits found in ${database}`;
      }

      let formatted = `✅ BLAST ${program.toUpperCase()} Results (${database})\n`;
      formatted += "=".repeat(40) + "\n\n";

      search.hits.slice(0, 5).forEach((hit, i) => {
        const hsp = hit.hsps?.[0];
        if (hsp) {
          formatted += `Hit ${i + 1}:\n`;
          formatted += `  ID: ${hit.description?.[0]?.accession || 'N/A'}\n`;
          formatted += `  Title: ${(hit.description?.[0]?.title || 'N/A').substring(0, 80)}...\n`;
          formatted += `  Identity: ${Math.round((hsp.identity / hsp.align_len) * 100)}%\n`;
          formatted += `  E-value: ${hsp.evalue}\n`;
          formatted += `  Score: ${hsp.bit_score}\n\n`;
        }
      });

      return formatted;

    } catch (error) {
      return `❌ Error formatting results: ${error.message}`;
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Stable Bio BLAST MCP server running");
  }
}

const server = new StableOnlineBlastServer();
server.run().catch(console.error);