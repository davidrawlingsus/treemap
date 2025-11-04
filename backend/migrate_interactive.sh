#!/bin/bash
# Interactive script to migrate data from dev to production

set -e

echo "🚀 Railway Data Migration: Dev → Production"
echo "=========================================="
echo ""

# Get dev database URL
if [ -z "$DEV_DATABASE_URL" ]; then
    echo "📥 Step 1: Get DEV database URL"
    echo ""
    echo "Run these commands in another terminal:"
    echo "  railway environment dev  # or your dev environment name"
    echo "  railway variables DATABASE_URL"
    echo ""
    echo "Or get it from Railway dashboard: Settings → Variables → DATABASE_URL"
    echo ""
    read -p "Enter DEV DATABASE_URL: " DEV_DATABASE_URL
    export DEV_DATABASE_URL
    echo ""
fi

# Get prod database URL
if [ -z "$PROD_DATABASE_URL" ]; then
    echo "📥 Step 2: Get PRODUCTION database URL"
    echo ""
    echo "Run these commands in another terminal:"
    echo "  railway environment production"
    echo "  railway variables DATABASE_URL"
    echo ""
    echo "Or get it from Railway dashboard: Settings → Variables → DATABASE_URL"
    echo ""
    read -p "Enter PROD DATABASE_URL: " PROD_DATABASE_URL
    export PROD_DATABASE_URL
    echo ""
fi

echo "✅ Database URLs configured"
echo "   DEV:  ${DEV_DATABASE_URL:0:50}..."
echo "   PROD: ${PROD_DATABASE_URL:0:50}..."
echo ""

# Confirm
echo "⚠️  WARNING: This will copy data from DEV to PRODUCTION"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Migration cancelled"
    exit 1
fi

echo ""
echo "🚀 Starting migration..."
echo ""

# Run the migration
venv/bin/python migrate_data_dev_to_prod.py

echo ""
echo "✅ Migration complete!"



