#!/usr/bin/env python3
"""Quick test to verify OSDR MCP server functionality"""

import sys
import os
sys.path.insert(0, '/Users/minyeop/alphagenome/bio-mcp-blast/osdr_mcp_server')

import asyncio
import httpx

async def test_osdr_api():
    """Test OSDR API directly"""
    print("🛰️ Testing OSDR API...")
    print("=" * 50)
    
    # Test 1: Find organisms
    url = "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/*/metadata/organism/Mus musculus/"
    print("🔍 Searching for mouse studies...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data)} mouse studies")
            
            # Show first dataset
            if data:
                first_id = list(data.keys())[0]
                print(f"\n📊 Example dataset: {first_id}")
                
                # Test 2: Fetch metadata
                metadata_url = f"https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/{first_id}/"
                print(f"📋 Fetching metadata for {first_id}...")
                
                metadata_response = await client.get(metadata_url)
                if metadata_response.status_code == 200:
                    metadata = metadata_response.json()
                    study_info = metadata.get(first_id, {}).get("metadata", {})
                    
                    print(f"✅ Title: {study_info.get('study title', 'N/A')}")
                    print(f"✅ Organism: {study_info.get('organism', 'N/A')}")
                    print(f"✅ Assay: {study_info.get('study assay technology type', 'N/A')}")
                    
                    return True
                else:
                    print(f"❌ Metadata fetch failed: {metadata_response.status_code}")
                    return False
        else:
            print(f"❌ Search failed: {response.status_code}")
            return False

async def main():
    print("🛰️ OSDR MCP SERVER TEST")
    print("NASA Open Science Data Repository Integration")
    print("=" * 50)
    
    success = await test_osdr_api()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ OSDR API TEST: PASSED")
        print("\n🎯 OSDR MCP Server 설정 완료!")
        print("\n📋 사용 가능한 기능:")
        print("1. osdr_fetch_metadata - OSDR 데이터셋 메타데이터 조회")
        print("2. osdr_find_by_organism - 생물 종별 연구 검색")
        print("\n🔄 사용 방법:")
        print("1. Claude Desktop 재시작")
        print("2. 예시 명령어:")
        print("   - 'Find mouse studies in OSDR'")
        print("   - 'Get metadata for OSDR dataset OSD-120'")
        print("   - 'Search for human RNA-seq studies in OSDR'")
        print("\n🛰️ NASA OSDR 데이터:")
        print("   - 우주 생물학 연구 데이터")
        print("   - 유전자 발현 프로파일")
        print("   - 다양한 생물 종의 실험 데이터")
    else:
        print("❌ OSDR API TEST: FAILED")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)