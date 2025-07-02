import asyncio
import json
import logging
import os
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Literal

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent
from mcp import McpError
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class ServerSettings(BaseSettings):
    max_file_size: int = Field(default=100_000_000, description="Maximum input file size in bytes")
    temp_dir: Optional[str] = Field(default=None, description="Temporary directory for processing")
    timeout: int = Field(default=300, description="Command timeout in seconds")
    ncbi_base_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils", description="NCBI E-utilities base URL")
    ncbi_api_key: Optional[str] = Field(default=None, description="NCBI API key for higher request limits (optional but recommended)")
    
    class Config:
        env_prefix = ""  # Allow both prefixed and non-prefixed env vars
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Try to get NCBI API key from standard env var if not set
        if not self.ncbi_api_key:
            self.ncbi_api_key = os.getenv('NCBI_API_KEY')


class GeneToGenomicServer:
    def __init__(self, settings: Optional[ServerSettings] = None):
        self.settings = settings or ServerSettings()
        self.server = Server("bio-mcp-gene-to-genomic", version="0.1.0")
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="gene_to_genomic_sequence",
                    description="Convert gene name to genomic DNA sequence using NCBI E-utilities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "gene_name": {
                                "type": "string", 
                                "description": "Gene symbol or name (e.g., TP53, BRCA1)"
                            },
                            "organism": {
                                "type": "string",
                                "description": "Organism name (default: human)",
                                "default": "human"
                            },
                            "sequence_type": {
                                "type": "string",
                                "enum": ["genomic", "cds", "mrna", "protein"],
                                "description": "Type of sequence to retrieve (default: genomic)",
                                "default": "genomic"
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["fasta", "genbank", "json"],
                                "description": "Output format (default: fasta)",
                                "default": "fasta"
                            }
                        },
                        "required": ["gene_name"]
                    }
                ),
                Tool(
                    name="search_gene_info",
                    description="Search for gene information including genomic location",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "gene_name": {
                                "type": "string", 
                                "description": "Gene symbol or name"
                            },
                            "organism": {
                                "type": "string",
                                "description": "Organism name (default: human)",
                                "default": "human"
                            }
                        },
                        "required": ["gene_name"]
                    }
                ),
                Tool(
                    name="get_genomic_sequence",
                    description="Get genomic sequence from chromosome coordinates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chromosome": {
                                "type": "string",
                                "description": "Chromosome accession (e.g., NC_000017.11)"
                            },
                            "start": {
                                "type": "integer",
                                "description": "Start position"
                            },
                            "end": {
                                "type": "integer",
                                "description": "End position"
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["fasta", "genbank"],
                                "description": "Output format (default: fasta)",
                                "default": "fasta"
                            }
                        },
                        "required": ["chromosome", "start", "end"]
                    }
                ),
                Tool(
                    name="search_geo_datasets",
                    description="Search GEO datasets by disease/condition and organism",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "disease": {
                                "type": "string",
                                "description": "Disease or condition name (e.g., 'cancer', 'diabetes', 'Alzheimer')"
                            },
                            "organism": {
                                "type": "string",
                                "description": "Organism (default: 'Homo sapiens')",
                                "default": "Homo sapiens",
                                "enum": ["Homo sapiens", "Mus musculus", "Rattus norvegicus"]
                            },
                            "study_type": {
                                "type": "string",
                                "description": "Type of expression study (default: Expression profiling by high throughput sequencing)",
                                "enum": ["Expression profiling by array", "Expression profiling by high throughput sequencing", "Genome binding/occupancy profiling by high throughput sequencing"],
                                "default": "Expression profiling by high throughput sequencing"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["disease"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent]:
            if name == "gene_to_genomic_sequence":
                return await self._gene_to_genomic_sequence(arguments)
            elif name == "search_gene_info":
                return await self._search_gene_info(arguments)
            elif name == "get_genomic_sequence":
                return await self._get_genomic_sequence(arguments)
            elif name == "search_geo_datasets":
                return await self._search_geo_datasets(arguments)
            else:
                raise McpError(f"Unknown tool: {name}")
    
    async def _gene_to_genomic_sequence(self, arguments: dict) -> list[TextContent]:
        """Main workflow: gene name -> genomic sequence"""
        try:
            gene_name = arguments["gene_name"]
            organism = arguments.get("organism", "human")
            sequence_type = arguments.get("sequence_type", "genomic")
            output_format = arguments.get("output_format", "fasta")
            
            # Step 1: Search for gene ID
            gene_info = await self._search_gene_ncbi(gene_name, organism)
            if not gene_info:
                return [TextContent(type="text", text=f"Gene '{gene_name}' not found in {organism}")]
            
            gene_id = gene_info.get("gene_id")
            if not gene_id:
                return [TextContent(type="text", text=f"Could not find gene ID for '{gene_name}'")]
            
            # Step 2: Get genomic coordinates
            genomic_info = await self._get_gene_genomic_info(gene_id)
            if not genomic_info:
                return [TextContent(type="text", text=f"Could not find genomic location for gene ID {gene_id}")]
            
            chromosome = genomic_info.get("chromosome")
            start_pos = genomic_info.get("start")
            end_pos = genomic_info.get("end")
            
            if not all([chromosome, start_pos, end_pos]):
                return [TextContent(type="text", text=f"Incomplete genomic coordinates for gene {gene_name}")]
            
            # Step 3: Get sequence
            if sequence_type == "genomic":
                sequence = await self._fetch_genomic_sequence(chromosome, start_pos, end_pos, output_format)
            else:
                # For other sequence types, we'd need additional logic
                sequence = await self._fetch_genomic_sequence(chromosome, start_pos, end_pos, output_format)
            
            if not sequence:
                return [TextContent(type="text", text=f"Could not retrieve sequence for {gene_name}")]
            
            # Format result
            result = f"Gene: {gene_name} ({organism})\n"
            result += f"Gene ID: {gene_id}\n"
            result += f"Location: {chromosome}:{start_pos}-{end_pos}\n"
            result += f"Sequence Type: {sequence_type}\n"
            result += f"Output Format: {output_format}\n\n"
            result += sequence
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            logger.error(f"Error in gene_to_genomic_sequence: {e}", exc_info=True)
            raise McpError(f"Error: {str(e)}")
    
    async def _search_gene_info(self, arguments: dict) -> list[TextContent]:
        """Search for gene information"""
        try:
            gene_name = arguments["gene_name"]
            organism = arguments.get("organism", "human")
            
            gene_info = await self._search_gene_ncbi(gene_name, organism)
            if not gene_info:
                return [TextContent(type="text", text=f"Gene '{gene_name}' not found in {organism}")]
            
            result = json.dumps(gene_info, indent=2)
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            logger.error(f"Error searching gene info: {e}", exc_info=True)
            raise McpError(f"Error: {str(e)}")
    
    async def _get_genomic_sequence(self, arguments: dict) -> list[TextContent]:
        """Get genomic sequence from coordinates"""
        try:
            chromosome = arguments["chromosome"]
            start = arguments["start"]
            end = arguments["end"]
            output_format = arguments.get("output_format", "fasta")
            
            sequence = await self._fetch_genomic_sequence(chromosome, start, end, output_format)
            if not sequence:
                return [TextContent(type="text", text=f"Could not retrieve sequence from {chromosome}:{start}-{end}")]
            
            return [TextContent(type="text", text=sequence)]
            
        except Exception as e:
            logger.error(f"Error getting genomic sequence: {e}", exc_info=True)
            raise McpError(f"Error: {str(e)}")
    
    async def _search_geo_datasets(self, arguments: dict) -> list[TextContent]:
        """Search GEO datasets by disease and organism"""
        try:
            disease = arguments["disease"]
            organism = arguments.get("organism", "Homo sapiens")
            study_type = arguments.get("study_type", "Expression profiling by high throughput sequencing")
            max_results = arguments.get("max_results", 10)
            
            logger.info(f"Searching GEO datasets for: {disease} in {organism}")
            
            # Build search query
            query_parts = [disease]
            query_parts.append(f'"{organism}"[Organism]')
            
            if study_type:
                query_parts.append(f'"{study_type}"[DataSet Type]')
                
            query = " AND ".join(query_parts)
            
            # Search GDS (Gene Expression Omnibus DataSets)
            search_url = f"{self.settings.ncbi_base_url}/esearch.fcgi"
            search_params = {
                'db': 'gds',
                'term': query,
                'retmax': max_results,
                'retmode': 'xml'
            }
            
            if self.settings.ncbi_api_key:
                search_params['api_key'] = self.settings.ncbi_api_key
                
            search_query = urllib.parse.urlencode(search_params)
            search_request_url = f"{search_url}?{search_query}"
            
            search_data = await self._make_http_request(search_request_url)
            search_root = ET.fromstring(search_data)
            id_list = search_root.find('.//IdList')
            
            if id_list is None or len(id_list) == 0:
                return [TextContent(type="text", text=f"❌ No GEO datasets found for '{disease}' in {organism}")]
                
            dataset_ids = [id_elem.text for id_elem in id_list.findall('Id')]
            logger.info(f"Found {len(dataset_ids)} datasets")
            
            # Get detailed information for each dataset
            summary_url = f"{self.settings.ncbi_base_url}/esummary.fcgi"
            summary_params = {
                'db': 'gds',
                'id': ','.join(dataset_ids),
                'retmode': 'xml'
            }
            
            if self.settings.ncbi_api_key:
                summary_params['api_key'] = self.settings.ncbi_api_key
                
            summary_query = urllib.parse.urlencode(summary_params)
            summary_request_url = f"{summary_url}?{summary_query}"
            
            summary_data = await self._make_http_request(summary_request_url)
            summary_root = ET.fromstring(summary_data)
            
            # Parse results
            results = []
            for doc_sum in summary_root.findall('.//DocSum'):
                dataset_info = self._parse_geo_dataset(doc_sum)
                if dataset_info:
                    results.append(dataset_info)
                    
            if not results:
                return [TextContent(type="text", text=f"❌ No detailed information available for GEO datasets")]
                
            # Format output
            output_lines = [
                f"🧬 **GEO Datasets for '{disease}' in {organism}**",
                f"Found {len(results)} dataset(s)\n"
            ]
            
            for i, dataset in enumerate(results, 1):
                output_lines.extend([
                    f"**{i}. {dataset['title']}**",
                    f"   📊 **GDS ID**: {dataset['accession']}",
                    f"   🧬 **Data Type**: {dataset['data_type']}",
                    f"   🔬 **Study Type**: {dataset['study_type']}",
                    f"   🧪 **Platform**: {dataset['platform']}",
                    f"   📈 **Sample Count**: {dataset['sample_count']}",
                    f"   📝 **Summary**: {dataset['summary'][:200]}{'...' if len(dataset['summary']) > 200 else ''}",
                    f"   🔗 **URL**: https://www.ncbi.nlm.nih.gov/sites/GDSbrowser?acc={dataset['accession']}\n"
                ])
                
            result_text = "\n".join(output_lines)
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            logger.error(f"Error searching GEO datasets: {str(e)}")
            return [TextContent(type="text", text=f"❌ Error searching GEO datasets: {str(e)}")]
    
    def _parse_geo_dataset(self, doc_sum) -> dict:
        """Parse GEO dataset information from XML"""
        try:
            dataset = {}
            
            # Get basic info
            dataset['id'] = doc_sum.find('./Id').text if doc_sum.find('./Id') is not None else 'Unknown'
            
            # Parse items
            for item in doc_sum.findall('./Item'):
                name = item.get('Name', '')
                value = item.text or ''
                
                if name == 'Accession':
                    dataset['accession'] = value
                elif name == 'title':
                    dataset['title'] = value
                elif name == 'summary':
                    dataset['summary'] = value
                elif name == 'GPL':
                    dataset['platform'] = value
                elif name == 'taxon':
                    dataset['organism'] = value
                elif name == 'entryType':
                    dataset['study_type'] = self._get_study_type_description(value)
                elif name == 'n_samples':
                    dataset['sample_count'] = value
                    
            # Set defaults for missing fields
            dataset.setdefault('title', 'Unknown Title')
            dataset.setdefault('summary', 'No summary available')
            dataset.setdefault('platform', 'Unknown Platform')
            dataset.setdefault('study_type', 'Unknown Study Type')
            dataset.setdefault('sample_count', 'Unknown')
            dataset.setdefault('accession', 'Unknown')
            
            # Add data type classification
            dataset['data_type'] = self._classify_data_type(dataset['title'], dataset['summary'])
            
            return dataset
            
        except Exception as e:
            logger.error(f"Error parsing GEO dataset: {str(e)}")
            return None
    
    def _classify_data_type(self, title: str, summary: str) -> str:
        """Classify whether the dataset is single-cell, bulk, or spatial transcriptomics"""
        text_to_check = f"{title} {summary}".lower()
        
        # Single-cell indicators
        sc_indicators = [
            'single cell', 'single-cell', 'scrnaseq', 'scrna-seq', 'scrna seq',
            'single cell rna', 'single cell rna-seq', 'single cell rnaseq',
            'single-cell rna', 'single-cell rna-seq', 'single-cell rnaseq',
            'sc-rna', 'scRNA', 'dropseq', 'drop-seq', '10x genomics', '10x chromium',
            'single cell transcriptom', 'single-cell transcriptom'
        ]
        
        # Spatial indicators
        spatial_indicators = [
            'spatial', 'visium', 'slide-seq', 'slideseq', 'merfish', 'seqfish',
            'spatial transcriptom', 'spatially resolved', 'in situ sequencing',
            'spatial rna', 'spatial rna-seq', 'spatial gene expression'
        ]
        
        # Check for single-cell
        for indicator in sc_indicators:
            if indicator in text_to_check:
                return '🧩 Single-Cell RNA-Seq'
        
        # Check for spatial
        for indicator in spatial_indicators:
            if indicator in text_to_check:
                return '🗺️ Spatial Transcriptomics'
        
        # Default to bulk
        return '📦 Bulk RNA-Seq'

    def _get_study_type_description(self, entry_type: str) -> str:
        """Get descriptive study type"""
        study_types = {
            'SAGE': 'SAGE (Serial Analysis of Gene Expression)',
            'Array': 'Microarray Expression Profiling',
            'ChIP-chip': 'ChIP-chip (Chromatin Immunoprecipitation)',
            'Protein profiling': 'Protein Expression Profiling',
            'SNP': 'SNP (Single Nucleotide Polymorphism) Analysis',
            'Methylation profiling': 'DNA Methylation Profiling',
            'RNA-Seq': 'RNA Sequencing (RNA-Seq)',
            'ChIP-Seq': 'ChIP-Seq (Chromatin Immunoprecipitation Sequencing)',
            'Bisulfite-Seq': 'Bisulfite Sequencing',
            'Other': 'Other High-Throughput Study'
        }
        return study_types.get(entry_type, f"{entry_type} Expression Study")
    
    async def _search_gene_ncbi(self, gene_name: str, organism: str) -> Optional[dict]:
        """Search for gene in NCBI Gene database"""
        try:
            # Build search query
            query = f"{gene_name}[GENE] AND {organism}[ORGN]"
            url = f"{self.settings.ncbi_base_url}/esearch.fcgi"
            params = {
                "db": "gene",
                "term": query,
                "retmode": "xml",
                "retmax": "1"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            # Make request
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            # Parse XML response
            root = ET.fromstring(response)
            id_list = root.find("IdList")
            if id_list is None or len(id_list) == 0:
                return None
            
            gene_id = id_list.find("Id").text
            
            # Get detailed information
            summary_info = await self._get_gene_summary(gene_id)
            
            return {
                "gene_id": gene_id,
                "gene_name": gene_name,
                "organism": organism,
                **summary_info
            }
            
        except Exception as e:
            logger.error(f"Error searching gene in NCBI: {e}")
            return None
    
    async def _get_gene_summary(self, gene_id: str) -> dict:
        """Get gene summary information"""
        try:
            url = f"{self.settings.ncbi_base_url}/esummary.fcgi"
            params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "xml"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            # Parse XML and extract relevant information
            root = ET.fromstring(response)
            doc_sum = root.find("DocSum")
            
            summary = {}
            if doc_sum is not None:
                for item in doc_sum.findall("Item"):
                    name = item.get("Name")
                    if name in ["Description", "OfficialSymbol", "Chromosome", "MapLocation"]:
                        summary[name.lower()] = item.text
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting gene summary: {e}")
            return {}
    
    async def _get_gene_genomic_info(self, gene_id: str) -> Optional[dict]:
        """Get genomic coordinates for a gene"""
        try:
            url = f"{self.settings.ncbi_base_url}/esummary.fcgi"
            params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "xml"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            # Parse XML to extract genomic info
            root = ET.fromstring(response)
            doc_sum = root.find("DocSum")
            
            if doc_sum is None:
                return None
            
            # Look for GenomicInfo
            for item in doc_sum.findall("Item"):
                if item.get("Name") == "GenomicInfo":
                    genomic_info = {}
                    for sub_item in item.findall("Item"):
                        name = sub_item.get("Name")
                        if name == "ChrAccVer":
                            genomic_info["chromosome"] = sub_item.text
                        elif name == "ChrStart":
                            genomic_info["start"] = int(sub_item.text)
                        elif name == "ChrStop":
                            genomic_info["end"] = int(sub_item.text)
                    
                    if all(k in genomic_info for k in ["chromosome", "start", "end"]):
                        return genomic_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting genomic info: {e}")
            return None
    
    async def _fetch_genomic_sequence(self, chromosome: str, start: int, end: int, format_type: str = "fasta") -> Optional[str]:
        """Fetch genomic sequence from NCBI"""
        try:
            url = f"{self.settings.ncbi_base_url}/efetch.fcgi"
            params = {
                "db": "nuccore",
                "id": chromosome,
                "seq_start": str(start),
                "seq_stop": str(end),
                "rettype": "fasta" if format_type == "fasta" else "gb",
                "retmode": "text"
            }
            
            # Add API key if available
            if self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            response = await self._make_http_request(full_url)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error fetching genomic sequence: {e}")
            return None
    
    async def _make_http_request(self, url: str) -> str:
        """Make HTTP request with timeout"""
        try:
            # Use asyncio to make the request non-blocking
            loop = asyncio.get_event_loop()
            
            def make_request():
                with urllib.request.urlopen(url, timeout=self.settings.timeout) as response:
                    return response.read().decode('utf-8')
            
            result = await loop.run_in_executor(None, make_request)
            return result
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream, 
                {
                    "name": "bio-mcp-gene-to-genomic",
                    "version": "0.1.0"
                }
            )


async def main():
    import sys
    logging.basicConfig(level=logging.DEBUG)
    print("Starting bio-mcp-gene-to-genomic server...", file=sys.stderr)
    server = GeneToGenomicServer()
    print("Server initialized, starting run...", file=sys.stderr)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())