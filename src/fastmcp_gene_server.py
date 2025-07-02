#!/usr/bin/env python3
"""
FastMCP Gene-to-Genomic Server
Simple and reliable implementation using FastMCP
"""

import asyncio
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import logging
import sys
from typing import Optional

import fastmcp

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# NCBI Configuration
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = os.getenv('NCBI_API_KEY')  # Set via environment variable

# Create FastMCP server
mcp = fastmcp.FastMCP("Gene-to-Genomic")

@mcp.tool()
def search_geo_datasets(disease: str, organism: str = "Homo sapiens", study_type: str = "Expression profiling by high throughput sequencing", max_results: int = 10) -> str:
    """
    Search GEO datasets by disease/condition and organism.
    
    Args:
        disease: Disease or condition name (e.g., 'cancer', 'diabetes', 'Alzheimer')
        organism: Organism name (default: Homo sapiens)
        study_type: Type of expression study (default: Expression profiling by high throughput sequencing)
        max_results: Maximum number of results (1-50, default: 10)
    
    Returns:
        Formatted list of GEO datasets with study details and methodology information
    """
    try:
        logger.info(f"Searching GEO datasets for: {disease} in {organism}")
        
        # Build search query
        query_parts = [disease]
        query_parts.append(f'"{organism}"[Organism]')
        
        if study_type:
            query_parts.append(f'"{study_type}"[DataSet Type]')
            
        query = " AND ".join(query_parts)
        
        # Search GDS (Gene Expression Omnibus DataSets)
        search_url = f"{NCBI_BASE_URL}/esearch.fcgi"
        search_params = {
            'db': 'gds',
            'term': query,
            'retmax': max_results,
            'retmode': 'xml'
        }
        
        if NCBI_API_KEY:
            search_params['api_key'] = NCBI_API_KEY
            
        search_query = urllib.parse.urlencode(search_params)
        search_request = urllib.request.Request(f"{search_url}?{search_query}")
        
        with urllib.request.urlopen(search_request) as response:
            search_data = response.read().decode('utf-8')
            
        search_root = ET.fromstring(search_data)
        id_list = search_root.find('.//IdList')
        
        if id_list is None or len(id_list) == 0:
            return f"❌ No GEO datasets found for '{disease}' in {organism}"
            
        dataset_ids = [id_elem.text for id_elem in id_list.findall('Id')]
        logger.info(f"Found {len(dataset_ids)} datasets")
        
        # Get detailed information
        summary_url = f"{NCBI_BASE_URL}/esummary.fcgi"
        summary_params = {
            'db': 'gds',
            'id': ','.join(dataset_ids),
            'retmode': 'xml'
        }
        
        if NCBI_API_KEY:
            summary_params['api_key'] = NCBI_API_KEY
            
        summary_query = urllib.parse.urlencode(summary_params)
        summary_request = urllib.request.Request(f"{summary_url}?{summary_query}")
        
        with urllib.request.urlopen(summary_request) as response:
            summary_data = response.read().decode('utf-8')
            
        summary_root = ET.fromstring(summary_data)
        
        # Parse results
        results = []
        for doc_sum in summary_root.findall('.//DocSum'):
            dataset_info = parse_geo_dataset(doc_sum)
            if dataset_info:
                results.append(dataset_info)
                
        if not results:
            return f"❌ No detailed information available for GEO datasets"
            
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
            
        return "\n".join(output_lines)
        
    except Exception as e:
        logger.error(f"Error searching GEO datasets: {str(e)}")
        return f"❌ Error searching GEO datasets: {str(e)}"

@mcp.tool()
def gene_to_sequence(gene_name: str, organism: str = "human") -> str:
    """
    Convert gene name to genomic DNA sequence using NCBI E-utilities.
    
    Args:
        gene_name: Gene symbol (e.g., TP53, BRCA1)
        organism: Organism name (default: human)
    
    Returns:
        Genomic DNA sequence in FASTA format with location information
    """
    try:
        logger.info(f"Processing gene: {gene_name} ({organism})")
        
        # Step 1: Search for gene ID
        gene_id = search_gene(gene_name, organism)
        if not gene_id:
            return f"❌ Gene '{gene_name}' not found in {organism}"
        
        logger.info(f"Found gene ID: {gene_id}")
        
        # Step 2: Get genomic coordinates
        coords = get_coordinates(gene_id)
        if not coords:
            return f"❌ Genomic coordinates not found for {gene_name}"
        
        logger.info(f"Found coordinates: {coords}")
        
        # Step 3: Fetch sequence
        sequence = fetch_sequence(coords["chr"], coords["start"], coords["end"])
        if not sequence:
            return f"❌ Sequence not available for {gene_name}"
        
        # Format result
        result = f"🧬 Gene: {gene_name} ({organism})\n"
        result += f"📍 Location: {coords['chr']}:{coords['start']:,}-{coords['end']:,}\n"
        result += f"📏 Length: {coords['end'] - coords['start']:,} bp\n\n"
        result += sequence
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing {gene_name}: {e}")
        return f"❌ Error: {str(e)}"

def search_gene(gene_name: str, organism: str) -> Optional[str]:
    """Search for gene ID in NCBI Gene database"""
    try:
        query = f"{gene_name}[GENE] AND {organism}[ORGN]"
        params = {
            "db": "gene",
            "term": query,
            "retmode": "xml",
            "retmax": "1"
        }
        
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        
        url = f"{NCBI_BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        response = http_request(url)
        
        root = ET.fromstring(response)
        id_list = root.find("IdList")
        if id_list is not None and len(id_list) > 0:
            return id_list.find("Id").text
        return None
        
    except Exception as e:
        logger.error(f"Gene search error: {e}")
        return None

def get_coordinates(gene_id: str) -> Optional[dict]:
    """Get genomic coordinates for gene"""
    try:
        params = {
            "db": "gene",
            "id": gene_id,
            "retmode": "xml"
        }
        
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        
        url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
        response = http_request(url)
        
        root = ET.fromstring(response)
        doc_sum = root.find("DocumentSummary")
        if doc_sum is None:
            doc_sum = root.find(".//DocumentSummary")
        
        if doc_sum is not None:
            # Look for GenomicInfo/GenomicInfoType
            genomic_info = doc_sum.find("GenomicInfo")
            if genomic_info is not None:
                genomic_info_type = genomic_info.find("GenomicInfoType")
                if genomic_info_type is not None:
                    coords = {}
                    
                    chr_acc = genomic_info_type.find("ChrAccVer")
                    chr_start = genomic_info_type.find("ChrStart")
                    chr_stop = genomic_info_type.find("ChrStop")
                    
                    if chr_acc is not None and chr_start is not None and chr_stop is not None:
                        coords["chr"] = chr_acc.text
                        start_pos = int(chr_start.text)
                        stop_pos = int(chr_stop.text)
                        
                        # NCBI sometimes has start > stop (reverse strand)
                        coords["start"] = min(start_pos, stop_pos)
                        coords["end"] = max(start_pos, stop_pos)
                        
                        return coords
        
        return None
        
    except Exception as e:
        logger.error(f"Coordinates error: {e}")
        return None

def fetch_sequence(chromosome: str, start: int, end: int) -> Optional[str]:
    """Fetch genomic sequence from NCBI"""
    try:
        params = {
            "db": "nuccore",
            "id": chromosome,
            "seq_start": str(start),
            "seq_stop": str(end),
            "rettype": "fasta",
            "retmode": "text"
        }
        
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        
        url = f"{NCBI_BASE_URL}/efetch.fcgi?{urllib.parse.urlencode(params)}"
        response = http_request(url)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Sequence fetch error: {e}")
        return None

def parse_geo_dataset(doc_sum) -> Optional[dict]:
    """Parse GEO dataset information from XML DocSum"""
    try:
        dataset = {}
        
        # Get basic info
        id_elem = doc_sum.find('Id')
        if id_elem is not None:
            dataset['id'] = id_elem.text
        
        # Parse Items
        items = doc_sum.findall('.//Item')
        for item in items:
            name = item.get('Name', '')
            
            if name == 'Accession':
                dataset['accession'] = item.text or ''
            elif name == 'title':
                dataset['title'] = item.text or ''
            elif name == 'summary':
                dataset['summary'] = item.text or ''
            elif name == 'GPL':
                dataset['platform'] = item.text or ''
            elif name == 'SSInfo':
                dataset['sample_count'] = item.text or '0'
            elif name == 'gdsType':
                dataset['study_type'] = get_study_type_description(item.text or '')
        
        # Ensure required fields exist
        if not dataset.get('accession'):
            return None
            
        # Set defaults for missing fields
        dataset.setdefault('title', 'No title available')
        dataset.setdefault('summary', 'No summary available')
        dataset.setdefault('platform', 'Unknown platform')
        dataset.setdefault('sample_count', '0')
        dataset.setdefault('study_type', 'Unknown study type')
        
        # Add data type classification
        dataset['data_type'] = classify_data_type(dataset['title'], dataset['summary'])
        
        return dataset
        
    except Exception as e:
        logger.error(f"Error parsing GEO dataset: {e}")
        return None

def classify_data_type(title: str, summary: str) -> str:
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

def get_study_type_description(study_type: str) -> str:
    """Get human-readable description of study type"""
    type_descriptions = {
        'Expression profiling by array': '🔬 Microarray Expression Analysis - Hybridization-based gene expression profiling using DNA microarrays',
        'Expression profiling by high throughput sequencing': '🧬 RNA-Seq Analysis - High-throughput transcriptome sequencing for comprehensive gene expression',
        'Genome binding/occupancy profiling by high throughput sequencing': '🎯 ChIP-Seq Analysis - Chromatin immunoprecipitation with sequencing for protein-DNA interactions',
        'Expression profiling by SAGE': '📊 SAGE Analysis - Serial analysis of gene expression using short sequence tags',
        'Expression profiling by RT-PCR': '🔍 RT-PCR Analysis - Reverse transcription PCR for targeted gene expression',
        'Protein profiling by protein array': '🧪 Protein Array - Protein expression profiling using antibody arrays',
        'Non-coding RNA profiling by high throughput sequencing': '🔗 ncRNA-Seq - Non-coding RNA sequencing for regulatory RNA analysis',
        'Methylation profiling by high throughput sequencing': '⚡ Bisulfite-Seq - DNA methylation profiling through bisulfite sequencing',
        'SNP genotyping by SNP array': '🧬 SNP Array - Single nucleotide polymorphism genotyping using DNA arrays',
        'Genome variation profiling by high throughput sequencing': '🔄 WGS/Exome-Seq - Whole genome or exome sequencing for variant detection'
    }
    
    return type_descriptions.get(study_type, f'🔬 {study_type}' if study_type else 'Unknown methodology')

def http_request(url: str) -> str:
    """Make HTTP request"""
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode('utf-8')

if __name__ == "__main__":
    print("Starting FastMCP Gene-to-Genomic Server...", file=sys.stderr)
    mcp.run()