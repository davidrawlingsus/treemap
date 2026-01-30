#!/bin/bash

# Railway startup script - runs migrations then starts the server
set -e

echo "🔍 Checking database connection..."
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."

echo "📦 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed! Check logs above"
    exit 1
fi

echo "🚀 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
