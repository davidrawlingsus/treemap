#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run the FastAPI server
echo "🚀 Starting FastAPI server..."
echo "📍 API will be available at http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --port 8000

