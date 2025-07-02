#!/usr/bin/env python3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"

def debug_genomic_info(gene_id="7157"):
    params = {
        "db": "gene",
        "id": gene_id,
        "retmode": "xml",
        "api_key": NCBI_API_KEY
    }
    
    url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
    
    with urllib.request.urlopen(url, timeout=30) as response:
        xml_data = response.read().decode('utf-8')
    
    root = ET.fromstring(xml_data)
    doc_sum = root.find("DocumentSummary")
    
    if doc_sum is not None:
        # Look specifically for GenomicInfo
        genomic_info = doc_sum.find("GenomicInfo")
        if genomic_info is not None:
            print("Found GenomicInfo:")
            for child in genomic_info:
                print(f"  Tag: {child.tag}")
                if child.text:
                    print(f"    Text: {child.text}")
                
                # Look for attributes
                for attr_name, attr_value in child.attrib.items():
                    print(f"    {attr_name}: {attr_value}")
                    
                # Look for nested elements
                for nested in child:
                    print(f"    Nested {nested.tag}: {nested.text}")
        else:
            print("GenomicInfo not found")
            print("Available elements:")
            for child in doc_sum:
                print(f"  {child.tag}: {child.text}")

if __name__ == "__main__":
    debug_genomic_info()