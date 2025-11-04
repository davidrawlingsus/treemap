#!/bin/bash
# Script to pull Railway environment variables for feature_branch environment
# and update .env file in backend directory

set -e

echo "🔐 Checking Railway authentication..."
railway whoami || {
    echo "❌ Not logged in to Railway. Please run: railway login"
    exit 1
}

echo "📋 Linking to Railway project..."
cd backend

# Link to project (if not already linked)
railway link 2>/dev/null || echo "Already linked or manual link required"

echo "🔗 Switching to feature_branch environment..."
railway environment feature_branch

echo "📥 Pulling environment variables..."
railway variables -e feature_branch --kv > .env.tmp

# Process variables and create .env file
echo "# Railway environment variables for feature_branch" > .env
echo "# Generated automatically - do not commit to git" >> .env
echo "" >> .env

# Add variables from Railway
if [ -s .env.tmp ]; then
    cat .env.tmp >> .env
    echo "✅ Environment variables pulled successfully!"
    echo ""
    echo "📝 Variables saved to backend/.env"
    echo ""
    echo "Current variables:"
    cat .env
else
    echo "⚠️  No variables found or error occurred"
    exit 1
fi

# Clean up temp file
rm -f .env.tmp

cd ..
echo ""
echo "✨ Done! Your backend/.env file has been updated."

