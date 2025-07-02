#!/bin/bash

echo "=== OSDR Organism Search Diagnosis ==="
echo ""

echo "1. Testing current API endpoint with 'human':"
echo "URL: https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/*/metadata/organism/human/"
curl -s "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/*/metadata/organism/human/" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total datasets returned: {len(data)}')
print(f'First 5 dataset IDs: {list(data.keys())[:5]}')
print(f'Sample structure for OSD-1:')
print(json.dumps(data['OSD-1'], indent=2))
"

echo ""
echo "========================================"
echo ""

echo "2. Testing individual dataset metadata to see actual organisms:"
for i in {1..10}; do
    echo "Checking OSD-$i:"
    curl -s "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-$i/" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    organism = data[f'OSD-{$i}']['metadata'].get('organism', 'NOT FOUND')
    title = data[f'OSD-{$i}']['metadata'].get('study title', 'NO TITLE')
    print(f'  Organism: {organism}')
    print(f'  Title: {title[:60]}...')
except Exception as e:
    print(f'  Error: {e}')
"
    echo ""
done

echo "========================================"
echo ""

echo "3. The problem: Current function returns organism=N/A for all results"
echo "Because the API structure is:"
echo '{"OSD-1": {"metadata": {"organism": {"human": null}}}}'
echo "But the function expects:"
echo '{"OSD-1": {"metadata": {"organism": "Homo sapiens"}}}'