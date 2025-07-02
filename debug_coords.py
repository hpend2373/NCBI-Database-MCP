#!/usr/bin/env python3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = "0e99890afeac38920e80efb7ef42539ef709"

def debug_coordinates(gene_id="7157"):
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
    print("Root tag:", root.tag)
    
    # Find DocumentSummary
    doc_sum = root.find("DocumentSummary")
    if doc_sum is None:
        doc_sum = root.find(".//DocumentSummary")
    
    if doc_sum is not None:
        print("Found DocumentSummary")
        
        # Look for GenomicInfo
        genomic_info = doc_sum.find("GenomicInfo")
        if genomic_info is not None:
            print("Found GenomicInfo")
            
            genomic_info_type = genomic_info.find("GenomicInfoType")
            if genomic_info_type is not None:
                print("Found GenomicInfoType")
                
                for child in genomic_info_type:
                    print(f"  {child.tag}: {child.text}")
                    
                chr_acc = genomic_info_type.find("ChrAccVer")
                chr_start = genomic_info_type.find("ChrStart")
                chr_stop = genomic_info_type.find("ChrStop")
                
                if all([chr_acc is not None, chr_start is not None, chr_stop is not None]):
                    print(f"SUCCESS: {chr_acc.text}:{chr_start.text}-{chr_stop.text}")
                else:
                    print(f"Missing elements: ChrAccVer={chr_acc}, ChrStart={chr_start}, ChrStop={chr_stop}")
            else:
                print("GenomicInfoType not found")
        else:
            print("GenomicInfo not found")
    else:
        print("DocumentSummary not found")
        print("Available top-level elements:")
        for child in root:
            print(f"  {child.tag}")

if __name__ == "__main__":
    debug_coordinates()