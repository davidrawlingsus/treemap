# Data Migration Guide: Dev → Production

## Quick Steps

1. **Get Dev Database URL:**
   ```bash
   railway environment dev  # or 'development' or your dev environment name
   railway variables DATABASE_URL
   # Copy the postgresql:// URL
   ```

2. **Get Production Database URL:**
   ```bash
   railway environment production
   railway variables DATABASE_URL
   # Copy the postgresql:// URL
   ```

3. **Run Migration:**
   ```bash
   cd backend
   export DEV_DATABASE_URL="postgresql://..."  # from step 1
   export PROD_DATABASE_URL="postgresql://..." # from step 2
   venv/bin/python migrate_data_dev_to_prod.py
   ```

   Or use command-line arguments:
   ```bash
   venv/bin/python migrate_data_dev_to_prod.py \
     --dev-url "postgresql://..." \
     --prod-url "postgresql://..."
   ```

## What the Migration Does

- Copies `users` table
- Copies `clients` table  
- Copies `memberships` table
- Copies `process_voc` table (can be large)
- Skips duplicates (safe to run multiple times)
- Shows progress as it copies

## Alternative: Get URLs from Railway Dashboard

1. Go to Railway dashboard
2. Select your project
3. Go to Settings → Variables
4. Find `DATABASE_URL` for each environment
5. Copy the values and use them in the migration command above



