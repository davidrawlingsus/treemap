#!/bin/bash

# Local testing script for Wattbike format
# This script will test the multi-format transformation system locally

set -e  # Exit on error

echo "=========================================="
echo "Wattbike Format Local Testing"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check if backend dependencies are installed
echo "Step 1: Checking backend setup..."
cd backend

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo -e "${GREEN}✓ Backend dependencies ready${NC}"
echo ""

# Step 2: Test format detection
echo "Step 2: Testing format detection..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from app.transformers import DataTransformer, DataSourceType
import json

try:
    print("  Loading Wattbike file...")
    with open('../data_sources/Wattbike - Customer Email Survey/rows.json', 'r') as f:
        data = json.load(f)
    
    print(f"  File loaded: {len(data)} rows")
    
    print("  Detecting format...")
    detected_format = DataTransformer.detect_format(data)
    
    if detected_format == DataSourceType.SURVEY_MULTI_REF:
        print(f"  ✓ Format detected correctly: {detected_format.value}")
        sys.exit(0)
    else:
        print(f"  ✗ Wrong format detected: {detected_format.value}")
        print(f"    Expected: survey_multi_ref")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Format detection passed${NC}"
else
    echo -e "${RED}✗ Format detection failed${NC}"
    exit 1
fi
echo ""

# Step 3: Test transformation
echo "Step 3: Testing data transformation..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from app.transformers import DataTransformer, DataSourceType
import json

try:
    print("  Loading sample data (first 10 rows)...")
    with open('../data_sources/Wattbike - Customer Email Survey/rows.json', 'r') as f:
        data = json.load(f)[:10]
    
    print(f"  Input: {len(data)} rows")
    
    print("  Transforming to normalized format...")
    normalized = DataTransformer.transform(data, DataSourceType.SURVEY_MULTI_REF)
    
    print(f"  Output: {len(normalized)} normalized rows")
    print(f"  Expansion ratio: {len(normalized) / len(data):.2f}x")
    
    # Validate structure
    if len(normalized) == 0:
        print("  ✗ No normalized rows produced")
        sys.exit(1)
    
    first_row = normalized[0]
    required_fields = ['row_id', 'text', 'topics', 'sentiment', 'metadata']
    
    print("  Validating normalized structure...")
    for field in required_fields:
        if field not in first_row:
            print(f"  ✗ Missing required field: {field}")
            sys.exit(1)
    
    print("  ✓ All required fields present")
    
    # Check metadata
    if 'ref_key' not in first_row['metadata']:
        print("  ✗ Missing ref_key in metadata")
        sys.exit(1)
    
    print("  ✓ ref_key preserved in metadata")
    
    # Print sample
    print("\n  Sample normalized row:")
    print(f"    row_id: {first_row['row_id']}")
    print(f"    text: {first_row['text'][:50]}..." if len(first_row['text']) > 50 else f"    text: {first_row['text']}")
    print(f"    topics: {len(first_row['topics'])} topic(s)")
    print(f"    sentiment: {first_row['sentiment']}")
    print(f"    ref_key: {first_row['metadata']['ref_key']}")
    
    sys.exit(0)
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Data transformation passed${NC}"
else
    echo -e "${RED}✗ Data transformation failed${NC}"
    exit 1
fi
echo ""

# Step 4: Check if backend is running
echo "Step 4: Checking backend server..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is already running${NC}"
    BACKEND_RUNNING=true
else
    echo -e "${YELLOW}Backend is not running. Starting it...${NC}"
    echo "  (This will run in the background)"
    
    # Start backend in background
    nohup python3 -m uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    
    # Wait for backend to start
    echo "  Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend started successfully${NC}"
            BACKEND_RUNNING=false
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${RED}✗ Backend failed to start${NC}"
        echo "  Check backend.log for errors"
        exit 1
    fi
fi
echo ""

# Step 5: Upload Wattbike file via API
echo "Step 5: Testing API upload..."
cd ..

UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8000/api/data-sources/upload \
    -F "file=@data_sources/Wattbike - Customer Email Survey/rows.json" \
    -F "name=Wattbike Test $(date +%Y%m%d_%H%M%S)" \
    -F "auto_detect=true")

echo "  Upload response:"
echo "$UPLOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE"

# Extract ID from response
DATA_SOURCE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$DATA_SOURCE_ID" ]; then
    echo -e "${RED}✗ Upload failed or couldn't extract ID${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Upload successful${NC}"
echo "  Data Source ID: $DATA_SOURCE_ID"
echo ""

# Step 6: Retrieve and verify normalized data
echo "Step 6: Verifying normalized data from API..."

RETRIEVE_RESPONSE=$(curl -s "http://localhost:8000/api/data-sources/$DATA_SOURCE_ID")

# Check if normalized
IS_NORMALIZED=$(echo "$RETRIEVE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['is_normalized'])" 2>/dev/null)
SOURCE_FORMAT=$(echo "$RETRIEVE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['source_format'])" 2>/dev/null)
RAW_DATA_COUNT=$(echo "$RETRIEVE_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['raw_data']))" 2>/dev/null)

echo "  is_normalized: $IS_NORMALIZED"
echo "  source_format: $SOURCE_FORMAT"
echo "  normalized row count: $RAW_DATA_COUNT"

if [ "$IS_NORMALIZED" = "True" ] && [ "$SOURCE_FORMAT" = "survey_multi_ref" ]; then
    echo -e "${GREEN}✓ Data normalized correctly${NC}"
else
    echo -e "${RED}✗ Data normalization issue${NC}"
    exit 1
fi
echo ""

# Step 7: Check frontend
echo "Step 7: Testing frontend..."
if [ -f "package.json" ]; then
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm install
    fi
    
    if pgrep -f "node.*server.js" > /dev/null; then
        echo -e "${GREEN}✓ Frontend is already running${NC}"
    else
        echo -e "${YELLOW}Starting frontend server...${NC}"
        nohup npm start > frontend.log 2>&1 &
        echo $! > frontend.pid
        sleep 3
        echo -e "${GREEN}✓ Frontend started${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}✓ Frontend available at: http://localhost:3000${NC}"
else
    echo -e "${YELLOW}⚠ No package.json found, skipping frontend test${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}✓ Format detection: Passed${NC}"
echo -e "${GREEN}✓ Data transformation: Passed${NC}"
echo -e "${GREEN}✓ API upload: Passed${NC}"
echo -e "${GREEN}✓ Data normalization: Passed${NC}"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Select 'Wattbike Test...' from the dropdown"
echo "3. Verify the visualization renders correctly"
echo "4. Test interactions (click topics, view verbatims)"
echo ""
echo "Data Source ID: $DATA_SOURCE_ID"
echo ""
echo "To stop servers:"
echo "  Backend: kill \$(cat backend.pid) 2>/dev/null"
echo "  Frontend: kill \$(cat frontend.pid) 2>/dev/null"
echo ""
echo -e "${GREEN}=========================================="
echo "✓ All automated tests passed!"
echo "==========================================${NC}"

