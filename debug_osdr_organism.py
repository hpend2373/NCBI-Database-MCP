#!/usr/bin/env python3
"""
Debug script to understand OSDR organism search issue
"""
import httpx
import asyncio
import json

async def test_organism_search():
    """Test different organism search approaches"""
    print("=== Testing OSDR Organism Search ===\n")
    
    # Test 1: Current implementation approach
    print("1. Testing current API endpoint approach:")
    url = "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/*/metadata/organism/human/"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        print(f"URL: {url}")
        print(f"Response keys: {list(data.keys())[:5]}...")
        print(f"Sample data structure: {json.dumps(data['OSD-1'], indent=2)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Check individual dataset approach
    print("2. Testing individual dataset metadata:")
    datasets_to_check = ["OSD-1", "OSD-2", "OSD-3", "OSD-4", "OSD-5"]
    
    for dataset_id in datasets_to_check:
        url = f"https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/{dataset_id}/"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()
            organism = data[dataset_id]['metadata'].get('organism', 'NOT FOUND')
            title = data[dataset_id]['metadata'].get('study title', 'NO TITLE')
            print(f"{dataset_id}: {organism} - {title[:50]}...")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Check what the problematic function returns
    print("3. Testing current function logic:")
    url = "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/*/metadata/organism/human/"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        
        # Simulate current function logic
        results = [
            {"dataset_id": dataset_id, "organism": details.get("metadata", {}).get("organism", "N/A")}
            for dataset_id, details in data.items()
        ]
        
        print(f"Function would return {len(results)} results:")
        for i, result in enumerate(results[:10]):
            print(f"  {result}")
            if i >= 9:
                print(f"  ... and {len(results) - 10} more")
                break

if __name__ == "__main__":
    asyncio.run(test_organism_search())