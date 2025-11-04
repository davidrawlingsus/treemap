#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Use the venv's Python directly (avoiding path issues with venv activation)
echo "🚀 Starting FastAPI server..."
echo "📍 API will be available at http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo ""
"$SCRIPT_DIR/venv/bin/python" -m uvicorn app.main:app --reload --port 8000


