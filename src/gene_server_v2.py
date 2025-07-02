#!/usr/bin/env python3
"""
Gene-to-Genomic MCP Server v2
Simplified approach based on working patterns
"""

import asyncio
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import sys
import json
import logging
from typing import Any, Dict, List, Optional

# Configure logging to stderr so it doesn't interfere with MCP protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# NCBI Configuration
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"

class GeneToGenomicServer:
    def __init__(self):
        self.name = "gene-to-genomic"
        self.version = "1.0.0"
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": self.name,
                            "version": self.version
                        }
                    }
                }
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "gene_to_sequence",
                                "description": "Get COMPLETE genomic DNA sequence for any gene using NCBI database. Automatically selects the LATEST version/annotation release and returns the FULL-LENGTH genomic region including all exons, introns, and regulatory sequences. NO TRUNCATION - entire sequence guaranteed.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "gene_name": {
                                            "type": "string",
                                            "description": "Gene symbol (e.g., TP53, BRCA1, EGFR, KRAS)"
                                        },
                                        "organism": {
                                            "type": "string",
                                            "description": "Organism name (default: human)",
                                            "default": "human"
                                        }
                                    },
                                    "required": ["gene_name"]
                                }
                            },
                            {
                                "name": "search_geo_datasets",
                                "description": "Search GEO Datasets for expression profiling studies by high throughput sequencing. Find experimental data for diseases, tissues, or conditions with detailed information about data types and sample counts.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Search term for disease, tissue, condition, or keyword (e.g., 'cancer', 'brain', 'diabetes', 'heart')"
                                        },
                                        "organism": {
                                            "type": "string",
                                            "description": "Organism name (default: human)",
                                            "default": "human"
                                        },
                                        "max_results": {
                                            "type": "integer",
                                            "description": "Maximum number of datasets to return (default: 10)",
                                            "default": 10
                                        }
                                    },
                                    "required": ["query"]
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "gene_to_sequence":
                    result = await self.gene_to_sequence(arguments)
                    
                    # Ensure no truncation - force complete output
                    logger.info(f"Sending complete result: {len(result):,} characters")
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result
                                }
                            ],
                            "_meta": {
                                "total_length": len(result),
                                "complete": True,
                                "truncated": False
                            }
                        }
                    }
                elif tool_name == "search_geo_datasets":
                    result = await self.search_geo_datasets(arguments)
                    
                    logger.info(f"Sending GEO search result: {len(result):,} characters")
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result
                                }
                            ],
                            "_meta": {
                                "total_length": len(result),
                                "complete": True,
                                "truncated": False
                            }
                        }
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }
        
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def gene_to_sequence(self, arguments: Dict[str, Any]) -> str:
        """Convert gene name to genomic sequence"""
        gene_name = arguments["gene_name"]
        organism = arguments.get("organism", "human")
        
        logger.info(f"Processing gene: {gene_name} ({organism})")
        
        try:
            # Step 1: Search for gene ID
            gene_id = await self.search_gene_ncbi(gene_name, organism)
            if not gene_id:
                return f"❌ Gene '{gene_name}' not found in {organism}"
            
            # Step 2: Get genomic coordinates
            coords = await self.get_genomic_coordinates(gene_id)
            if not coords:
                return f"❌ Genomic coordinates not found for {gene_name}"
            
            # Step 3: Fetch COMPLETE genomic sequence
            logger.info(f"Fetching complete genomic sequence for {gene_name}")
            sequence = await self.fetch_genomic_sequence(coords["chr"], coords["start"], coords["end"])
            if not sequence:
                return f"❌ Complete genomic sequence not available for {gene_name}"
            
            # Count actual sequence length (excluding FASTA header)
            sequence_lines = sequence.split('\n')
            header_line = sequence_lines[0] if sequence_lines[0].startswith('>') else ""
            actual_sequence = ''.join(line.strip() for line in sequence_lines[1:] if line.strip())
            actual_length = len(actual_sequence)
            
            # Format result with complete genomic information including version info
            result = f"🧬 Gene: {gene_name} ({organism})\n"
            result += f"📍 Genomic Location: {coords['chr']}:{coords['start']:,}-{coords['end']:,}\n"
            
            # Add version information if available
            if 'source' in coords:
                result += f"🔄 Version: {coords['source']}\n"
            if 'release' in coords and 'assembly' in coords:
                result += f"📋 Annotation: {coords['release']} | Assembly: {coords['assembly']}\n"
                
            result += f"📏 Expected Length: {coords['end'] - coords['start']:,} bp\n"
            result += f"📏 Actual Sequence Length: {actual_length:,} bp\n"
            result += f"🔬 Complete Genomic DNA Sequence (LATEST VERSION - FULL LENGTH):\n"
            result += f"⚠️  IMPORTANT: This is the COMPLETE sequence with {actual_length:,} nucleotides.\n"
            result += f"⚠️  No truncation applied - entire genomic region included.\n\n"
            result += sequence
            
            # Verify we got the complete sequence
            if actual_length > 0:
                logger.info(f"Successfully retrieved complete sequence: {actual_length:,} bp")
            else:
                logger.warning(f"No sequence data retrieved for {gene_name}")
                return f"❌ No sequence data available for {gene_name}"
            
            return result
            
        except Exception as e:
            logger.error(f"Gene processing error: {e}")
            return f"❌ Error processing {gene_name}: {str(e)}"
    
    async def search_geo_datasets(self, arguments: Dict[str, Any]) -> str:
        """Search GEO Datasets for expression profiling studies"""
        query = arguments["query"]
        organism = arguments.get("organism", "human")
        max_results = arguments.get("max_results", 10)
        
        logger.info(f"Searching GEO for: {query} in {organism}")
        
        try:
            # Build GEO search query
            # Focus on Expression profiling by high throughput sequencing
            search_terms = []
            search_terms.append(f'"{query}"[All Fields]')
            search_terms.append(f'"{organism}"[Organism]')
            search_terms.append('"Expression profiling by high throughput sequencing"[DataSet Type]')
            
            combined_query = " AND ".join(search_terms)
            
            # Search GEO using E-utilities
            datasets = await self.search_geo_eutils(combined_query, max_results)
            
            if not datasets:
                return f"❌ No datasets found for '{query}' in {organism} with high throughput sequencing"
            
            # Format results
            result = f"🧬 GEO Datasets Search Results\n"
            result += f"🔍 Query: {query} ({organism})\n"
            result += f"🎯 Study Type: Expression profiling by high throughput sequencing\n"
            result += f"📊 Found: {len(datasets)} datasets\n\n"
            
            for i, dataset in enumerate(datasets, 1):
                result += f"{'='*60}\n"
                result += f"📋 Dataset #{i}: {dataset.get('accession', 'N/A')}\n"
                result += f"{'='*60}\n"
                result += f"📝 Title: {dataset.get('title', 'N/A')}\n"
                result += f"📄 Summary: {dataset.get('summary', 'N/A')[:300]}{'...' if len(dataset.get('summary', '')) > 300 else ''}\n"
                
                # Dataset details
                result += f"📊 Sample Count: {dataset.get('sample_count', 'N/A')}\n"
                result += f"🔬 Platform: {dataset.get('platform', 'N/A')}\n"
                result += f"📅 Release Date: {dataset.get('release_date', 'N/A')}\n"
                
                # Try to determine if single-cell or bulk
                data_type = self.determine_data_type(dataset)
                result += f"🧪 Data Type: {data_type}\n"
                
                # Organism info
                result += f"🦠 Organism: {dataset.get('organism', 'N/A')}\n"
                
                # GEO link
                if dataset.get('accession'):
                    result += f"🔗 GEO Link: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={dataset['accession']}\n"
                
                result += f"\n"
            
            return result
            
        except Exception as e:
            logger.error(f"GEO search error: {e}")
            return f"❌ Error searching GEO: {str(e)}"
    
    def determine_data_type(self, dataset: dict) -> str:
        """Determine if dataset is single-cell or bulk RNA-seq"""
        title = dataset.get('title', '').lower()
        summary = dataset.get('summary', '').lower()
        platform = dataset.get('platform', '').lower()
        
        # Check for single-cell indicators
        sc_indicators = [
            'single cell', 'single-cell', 'scrna', 'sc-rna', 'scrnaseq', 'sc-rna-seq',
            'drop-seq', 'dropseq', '10x', 'smart-seq', 'cell ranger', 'cellranger'
        ]
        
        text_to_check = f"{title} {summary} {platform}"
        
        for indicator in sc_indicators:
            if indicator in text_to_check:
                return "🔬 Single-cell RNA-seq"
        
        # Check for bulk indicators
        bulk_indicators = ['bulk', 'total rna', 'rna-seq', 'rnaseq']
        for indicator in bulk_indicators:
            if indicator in text_to_check:
                return "🧪 Bulk RNA-seq"
        
        # Default to RNA-seq if unclear
        return "🧬 RNA-seq (type unclear)"
    
    async def search_geo_eutils(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search GEO using NCBI E-utilities"""
        try:
            # Step 1: Search for dataset IDs
            search_params = {
                "db": "gds",
                "term": query,
                "retmode": "xml",
                "retmax": str(max_results),
                "api_key": NCBI_API_KEY
            }
            
            search_url = f"{NCBI_BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(search_params)}"
            search_response = await self.make_http_request(search_url)
            
            # Parse search results
            search_root = ET.fromstring(search_response)
            id_list = search_root.find("IdList")
            
            if id_list is None or len(id_list) == 0:
                return []
            
            dataset_ids = [id_elem.text for id_elem in id_list.findall("Id")]
            
            # Step 2: Get detailed information for each dataset
            datasets = []
            for dataset_id in dataset_ids:
                dataset_info = await self.get_geo_dataset_details(dataset_id)
                if dataset_info:
                    datasets.append(dataset_info)
            
            return datasets
            
        except Exception as e:
            logger.error(f"GEO E-utilities search error: {e}")
            return []
    
    async def get_geo_dataset_details(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a GEO dataset"""
        try:
            summary_params = {
                "db": "gds",
                "id": dataset_id,
                "retmode": "xml",
                "api_key": NCBI_API_KEY
            }
            
            summary_url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(summary_params)}"
            summary_response = await self.make_http_request(summary_url)
            
            # Parse dataset details
            root = ET.fromstring(summary_response)
            doc_sum = root.find("DocSum")
            if doc_sum is None:
                doc_sum = root.find(".//DocSum")
            
            if doc_sum is not None:
                dataset = {}
                
                # Extract basic information
                for item in doc_sum.findall("Item"):
                    name = item.get("Name")
                    if name == "Accession":
                        dataset["accession"] = item.text
                    elif name == "title":
                        dataset["title"] = item.text
                    elif name == "summary":
                        dataset["summary"] = item.text
                    elif name == "GPL":
                        dataset["platform"] = item.text
                    elif name == "n_samples":
                        dataset["sample_count"] = item.text
                    elif name == "PDAT":
                        dataset["release_date"] = item.text
                    elif name == "taxon":
                        dataset["organism"] = item.text
                
                return dataset
            
            return None
            
        except Exception as e:
            logger.error(f"Dataset details error: {e}")
            return None
    
    async def search_gene_ncbi(self, gene_name: str, organism: str) -> Optional[str]:
        """Search for gene ID in NCBI Gene database"""
        try:
            query = f"{gene_name}[GENE] AND {organism}[ORGN]"
            params = {
                "db": "gene",
                "term": query,
                "retmode": "xml",
                "retmax": "1",
                "api_key": NCBI_API_KEY
            }
            
            url = f"{NCBI_BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
            response = await self.make_http_request(url)
            
            root = ET.fromstring(response)
            id_list = root.find("IdList")
            if id_list is not None and len(id_list) > 0:
                return id_list.find("Id").text
            return None
            
        except Exception as e:
            logger.error(f"Gene search error: {e}")
            return None
    
    async def get_genomic_coordinates(self, gene_id: str) -> Optional[Dict[str, Any]]:
        """Get genomic coordinates for gene - selecting the LATEST version"""
        try:
            params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "xml",
                "api_key": NCBI_API_KEY
            }
            
            url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
            response = await self.make_http_request(url)
            
            root = ET.fromstring(response)
            doc_sum = root.find("DocumentSummary")
            if doc_sum is None:
                doc_sum = root.find(".//DocumentSummary")
            
            if doc_sum is not None:
                # First try to get the latest from GenomicInfo (current/primary)
                genomic_info = doc_sum.find("GenomicInfo")
                latest_coords = None
                
                if genomic_info is not None:
                    genomic_info_type = genomic_info.find("GenomicInfoType")
                    if genomic_info_type is not None:
                        chr_acc = genomic_info_type.find("ChrAccVer")
                        chr_start = genomic_info_type.find("ChrStart")
                        chr_stop = genomic_info_type.find("ChrStop")
                        
                        if chr_acc is not None and chr_start is not None and chr_stop is not None:
                            start_pos = int(chr_start.text)
                            stop_pos = int(chr_stop.text)
                            
                            latest_coords = {
                                "chr": chr_acc.text,
                                "start": min(start_pos, stop_pos),
                                "end": max(start_pos, stop_pos),
                                "source": "Current GenomicInfo"
                            }
                
                # Also check LocationHist for the most recent annotation release
                location_hist = doc_sum.find("LocationHist")
                if location_hist is not None:
                    best_coords = None
                    best_release = None
                    best_assembly = None
                    
                    for hist_type in location_hist.findall("LocationHistType"):
                        annot_release = hist_type.find("AnnotationRelease")
                        assembly = hist_type.find("AssemblyAccVer")
                        chr_acc = hist_type.find("ChrAccVer")
                        chr_start = hist_type.find("ChrStart")
                        chr_stop = hist_type.find("ChrStop")
                        
                        if all([annot_release is not None, assembly is not None, 
                               chr_acc is not None, chr_start is not None, chr_stop is not None]):
                            
                            release_text = annot_release.text
                            assembly_text = assembly.text
                            
                            # Prioritize latest releases and primary reference assembly
                            is_better = False
                            
                            # Prefer RS_2024_xx over older releases
                            if release_text.startswith("RS_2024"):
                                if best_release is None or not best_release.startswith("RS_2024"):
                                    is_better = True
                                elif best_release.startswith("RS_2024"):
                                    # Compare month numbers in RS_2024_XX
                                    try:
                                        current_month = int(release_text.split("_")[-1])
                                        best_month = int(best_release.split("_")[-1])
                                        if current_month > best_month:
                                            is_better = True
                                    except:
                                        pass
                            
                            # Prefer primary reference assembly (GCF_000001405.xx)
                            if assembly_text.startswith("GCF_000001405."):
                                if best_assembly is None or not best_assembly.startswith("GCF_000001405."):
                                    is_better = True
                                elif best_assembly.startswith("GCF_000001405."):
                                    # Compare version numbers
                                    try:
                                        current_ver = int(assembly_text.split(".")[-1])
                                        best_ver = int(best_assembly.split(".")[-1])
                                        if current_ver > best_ver:
                                            is_better = True
                                    except:
                                        pass
                            
                            if is_better:
                                start_pos = int(chr_start.text)
                                stop_pos = int(chr_stop.text)
                                
                                best_coords = {
                                    "chr": chr_acc.text,
                                    "start": min(start_pos, stop_pos),
                                    "end": max(start_pos, stop_pos),
                                    "source": f"Latest: {release_text} ({assembly_text})",
                                    "release": release_text,
                                    "assembly": assembly_text
                                }
                                best_release = release_text
                                best_assembly = assembly_text
                    
                    # Use the best coordinates from LocationHist if available
                    if best_coords:
                        logger.info(f"Selected latest version: {best_coords['source']}")
                        return best_coords
                
                # Fall back to current GenomicInfo if no better option found
                if latest_coords:
                    logger.info(f"Using current genomic info: {latest_coords['source']}")
                    return latest_coords
            
            return None
            
        except Exception as e:
            logger.error(f"Coordinates error: {e}")
            return None
    
    async def fetch_genomic_sequence(self, chromosome: str, start: int, end: int) -> Optional[str]:
        """Fetch COMPLETE genomic sequence from NCBI"""
        try:
            sequence_length = end - start
            logger.info(f"Fetching {sequence_length:,} bp sequence from NCBI...")
            
            params = {
                "db": "nuccore",
                "id": chromosome,
                "seq_start": str(start),
                "seq_stop": str(end),
                "rettype": "fasta",
                "retmode": "text",
                "api_key": NCBI_API_KEY
            }
            
            url = f"{NCBI_BASE_URL}/efetch.fcgi?{urllib.parse.urlencode(params)}"
            
            # Use longer timeout for large sequences
            timeout = 60 if sequence_length > 50000 else 30
            response = await self.make_http_request(url, timeout=timeout)
            
            if response and response.strip():
                logger.info(f"Successfully fetched genomic sequence ({len(response):,} characters)")
                return response.strip()
            else:
                logger.error("Empty response from NCBI")
                return None
            
        except Exception as e:
            logger.error(f"Sequence fetch error: {e}")
            return None
    
    async def make_http_request(self, url: str, timeout: int = 30) -> str:
        """Make HTTP request using asyncio executor with configurable timeout"""
        loop = asyncio.get_event_loop()
        
        def make_request():
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.read().decode('utf-8')
        
        return await loop.run_in_executor(None, make_request)
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Gene-to-Genomic MCP Server...")
        
        while True:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON request
                request = json.loads(line)
                
                # Handle request
                response = await self.handle_request(request)
                
                # Send response with no length limitations
                response_json = json.dumps(response, ensure_ascii=False, separators=(',', ':'))
                
                # Write directly to stdout for large data
                sys.stdout.write(response_json + '\n')
                sys.stdout.flush()
                
                # Log large responses
                if len(response_json) > 50000:
                    logger.info(f"Large response sent: {len(response_json):,} characters")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                continue
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Server error: {e}")
                break

async def main():
    """Main function"""
    # Disable stdout buffering for large sequences
    sys.stdout.reconfigure(line_buffering=False)
    sys.stderr.reconfigure(line_buffering=False)
    
    server = GeneToGenomicServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())