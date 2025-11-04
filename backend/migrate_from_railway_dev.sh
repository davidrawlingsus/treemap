#!/bin/bash
# Script to migrate data from Railway dev environment to production
# This script gets DATABASE_URL from both environments and runs the migration

set -e

echo "🚀 Railway Data Migration: Dev → Production"
echo "=========================================="
echo ""

# Check if Railway CLI is available
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install it first:"
    echo "   npm i -g @railway/cli"
    exit 1
fi

# Check if logged in
echo "🔐 Checking Railway authentication..."
railway whoami || {
    echo "❌ Not logged in to Railway. Please run: railway login"
    exit 1
}

# Check if linked
echo "📋 Checking Railway project link..."
railway status || {
    echo "❌ Not linked to a project. Please run: railway link"
    exit 1
}

echo ""
echo "📥 Getting database URLs from Railway environments..."
echo ""

# Get DEV database URL
echo "🔍 Getting DEV environment DATABASE_URL..."
railway environment dev 2>/dev/null || railway environment development 2>/dev/null || echo "Switching to dev environment..."
railway variables --json > /tmp/railway_dev_vars.json 2>/dev/null || true

if [ -f /tmp/railway_dev_vars.json ]; then
    export DEV_DATABASE_URL=$(cat /tmp/railway_dev_vars.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('DATABASE_URL', ''))" 2>/dev/null || echo "")
    rm -f /tmp/railway_dev_vars.json
fi

if [ -z "$DEV_DATABASE_URL" ]; then
    echo "⚠️  Could not get DEV DATABASE_URL automatically"
    echo "   Trying alternative method..."
    export DEV_DATABASE_URL=$(railway variables DATABASE_URL 2>/dev/null | tail -1 || echo "")
fi

if [ -z "$DEV_DATABASE_URL" ]; then
    echo "⚠️  Please set it manually:"
    echo "   railway environment dev"
    echo "   railway variables DATABASE_URL"
    echo ""
    read -p "   Enter DEV DATABASE_URL: " DEV_DATABASE_URL
    export DEV_DATABASE_URL
fi

# Get PROD database URL
echo "🔍 Getting PRODUCTION environment DATABASE_URL..."
railway environment production 2>/dev/null || echo "Switching to production environment..."
railway variables --json > /tmp/railway_prod_vars.json 2>/dev/null || true

if [ -f /tmp/railway_prod_vars.json ]; then
    export PROD_DATABASE_URL=$(cat /tmp/railway_prod_vars.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('DATABASE_URL', ''))" 2>/dev/null || echo "")
    rm -f /tmp/railway_prod_vars.json
fi

if [ -z "$PROD_DATABASE_URL" ]; then
    echo "⚠️  Could not get PROD DATABASE_URL automatically"
    echo "   Trying alternative method..."
    export PROD_DATABASE_URL=$(railway variables DATABASE_URL 2>/dev/null | tail -1 || echo "")
fi

if [ -z "$PROD_DATABASE_URL" ]; then
    echo "⚠️  Please set it manually:"
    echo "   railway environment production"
    echo "   railway variables DATABASE_URL"
    echo ""
    read -p "   Enter PROD DATABASE_URL: " PROD_DATABASE_URL
    export PROD_DATABASE_URL
fi

echo ""
echo "✅ Database URLs configured"
echo "   DEV:  ${DEV_DATABASE_URL:0:50}..."
echo "   PROD: ${PROD_DATABASE_URL:0:50}..."
echo ""

# Confirm before proceeding
echo "⚠️  WARNING: This will copy data from DEV to PRODUCTION"
echo "   This will:"
echo "   - Copy users, clients, memberships from dev to prod"
echo "   - Copy all process_voc rows from dev to prod"
echo "   - Skip duplicates (won't overwrite existing data)"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Migration cancelled"
    exit 1
fi

echo ""
echo "🚀 Starting migration..."
echo ""

# Run the migration script
python3 migrate_data_dev_to_prod.py

echo ""
echo "✅ Migration complete!"
echo ""
echo "📊 Next steps:"
echo "   1. Verify data in production database"
echo "   2. Test the application with production data"
echo "   3. Check that client_uuid mappings are correct"

