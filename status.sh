#!/bin/bash

echo "🔍 Checking Visualizd Status..."
echo ""

# Check Backend
echo "Backend API (port 8000):"
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✅ Running"
    HEALTH=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
    echo "  Status: $HEALTH"
else
    echo "  ❌ Not running"
    echo "  Start with: cd backend && ./start.sh"
fi

echo ""

# Check Frontend
echo "Frontend Server (port 3000):"
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "  ✅ Running at http://localhost:3000"
else
    echo "  ❌ Not running"
    echo "  Start with: ./serve.sh"
fi

echo ""

# Check Data Sources
echo "Data Sources:"
if curl -s -f http://localhost:8000/api/data-sources > /dev/null 2>&1; then
    COUNT=$(curl -s http://localhost:8000/api/data-sources | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
    echo "  ✅ $COUNT data source(s) available"
    curl -s http://localhost:8000/api/data-sources | python3 -c "import sys, json; [print(f\"    - {ds['name']}\") for ds in json.load(sys.stdin)]"
else
    echo "  ❌ Cannot check (backend not running)"
fi

echo ""
echo "📍 Open: http://localhost:3000/index.html"


