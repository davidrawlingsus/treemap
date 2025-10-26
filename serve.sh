#!/bin/bash

echo "🌐 Starting local web server..."
echo "📍 Frontend available at http://localhost:3000"
echo "📍 Backend API at http://localhost:8000"
echo ""
echo "Press CTRL+C to stop"
echo ""

# Use Python's built-in HTTP server
python3 -m http.server 3000

