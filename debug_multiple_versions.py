#!/usr/bin/env python3
"""Debug script to see multiple genomic versions"""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"

def debug_gene_versions(gene_name="TP53", organism="human"):
    """Debug to see all genomic versions for a gene"""
    
    # Step 1: Search for gene ID
    query = f"{gene_name}[GENE] AND {organism}[ORGN]"
    params = {
        "db": "gene",
        "term": query,
        "retmode": "xml",
        "retmax": "5",  # Get multiple results
        "api_key": NCBI_API_KEY
    }
    
    url = f"{NCBI_BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    print(f"🔍 Search URL: {url}")
    
    with urllib.request.urlopen(url, timeout=30) as response:
        search_data = response.read().decode('utf-8')
    
    print("📊 Search Results:")
    root = ET.fromstring(search_data)
    id_list = root.find("IdList")
    
    if id_list is not None:
        gene_ids = [id_elem.text for id_elem in id_list.findall("Id")]
        print(f"Found {len(gene_ids)} gene IDs: {gene_ids}")
        
        # Get details for each gene ID
        for i, gene_id in enumerate(gene_ids):
            print(f"\n{'='*50}")
            print(f"🧬 Gene ID {gene_id} (Result #{i+1})")
            print(f"{'='*50}")
            
            # Get summary for this gene ID
            params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "xml",
                "api_key": NCBI_API_KEY
            }
            
            url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
            
            with urllib.request.urlopen(url, timeout=30) as response:
                summary_data = response.read().decode('utf-8')
            
            root = ET.fromstring(summary_data)
            doc_sum = root.find("DocumentSummary")
            if doc_sum is None:
                doc_sum = root.find(".//DocumentSummary")
            
            if doc_sum is not None:
                # Basic info
                name = doc_sum.find("Name")
                desc = doc_sum.find("Description") 
                organism_elem = doc_sum.find("Organism")
                
                print(f"📝 Name: {name.text if name is not None else 'N/A'}")
                print(f"📝 Description: {desc.text if desc is not None else 'N/A'}")
                if organism_elem is not None:
                    sci_name = organism_elem.find("ScientificName")
                    print(f"🔬 Organism: {sci_name.text if sci_name is not None else 'N/A'}")
                
                # Check for genomic info
                genomic_info = doc_sum.find("GenomicInfo")
                if genomic_info is not None:
                    print("📍 Genomic Locations:")
                    for genomic_type in genomic_info.findall("GenomicInfoType"):
                        chr_acc = genomic_type.find("ChrAccVer")
                        chr_start = genomic_type.find("ChrStart")
                        chr_stop = genomic_type.find("ChrStop")
                        
                        if all([chr_acc is not None, chr_start is not None, chr_stop is not None]):
                            print(f"  📌 {chr_acc.text}:{chr_start.text}-{chr_stop.text}")
                
                # Check for multiple location histories
                location_hist = doc_sum.find("LocationHist")
                if location_hist is not None:
                    print("📚 Location History:")
                    for hist_type in location_hist.findall("LocationHistType"):
                        annot_release = hist_type.find("AnnotationRelease")
                        assembly = hist_type.find("AssemblyAccVer")
                        chr_acc = hist_type.find("ChrAccVer")
                        chr_start = hist_type.find("ChrStart")
                        chr_stop = hist_type.find("ChrStop")
                        
                        print(f"  🔄 {annot_release.text if annot_release is not None else 'N/A'}")
                        print(f"     Assembly: {assembly.text if assembly is not None else 'N/A'}")
                        if all([chr_acc is not None, chr_start is not None, chr_stop is not None]):
                            print(f"     Location: {chr_acc.text}:{chr_start.text}-{chr_stop.text}")

if __name__ == "__main__":
    debug_gene_versions("TP53", "human")