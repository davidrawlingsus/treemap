#!/bin/bash
# Pull Railway environment variables for feature_branch environment

set -e

echo "🔗 Switching to feature_branch environment..."
railway environment feature_branch

echo "📥 Pulling environment variables..."
railway variables -e feature_branch --kv > .env

echo "✅ Environment variables saved to .env"
echo ""
echo "Variables:"
cat .env

