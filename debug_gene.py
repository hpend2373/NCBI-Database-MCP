#!/usr/bin/env python3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"

def debug_gene_summary(gene_id="7157"):
    params = {
        "db": "gene",
        "id": gene_id,
        "retmode": "xml",
        "api_key": NCBI_API_KEY
    }
    
    url = f"{NCBI_BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
    print(f"URL: {url}")
    
    with urllib.request.urlopen(url, timeout=30) as response:
        xml_data = response.read().decode('utf-8')
    
    print("Raw XML response:")
    print(xml_data[:1000] + "..." if len(xml_data) > 1000 else xml_data)
    
    root = ET.fromstring(xml_data)
    doc_sum = root.find("DocSum")
    
    if doc_sum is not None:
        print("\nAll items:")
        for item in doc_sum.findall("Item"):
            name = item.get("Name")
            print(f"  {name}: {item.text}")
            
            # Look for nested items
            for sub_item in item.findall("Item"):
                sub_name = sub_item.get("Name")
                print(f"    {sub_name}: {sub_item.text}")

if __name__ == "__main__":
    debug_gene_summary()