# Database Migrations Guide

## Problem: Missing magic_link_token Column

If you're seeing the error **"No magic link was requested for this email"**, it means the database migrations haven't been run yet, and the `magic_link_token` column doesn't exist in the `users` table.

## Solution 1: Automatic (Recommended)

The migrations now run automatically on Railway deployment via the `railway_start.sh` script.

**After pushing the latest changes:**
1. Railway will detect the new commit
2. It will redeploy
3. The startup script will run `alembic upgrade head`
4. Migrations will be applied automatically
5. Server will start

Check the Railway deployment logs to confirm you see:
```
📦 Running database migrations...
✅ Migrations completed successfully
🚀 Starting FastAPI server...
```

## Solution 2: Manual Migration (If Needed)

If you need to run migrations manually via Railway CLI:

### Prerequisites
```bash
# Install Railway CLI if you haven't
npm install -g @railway/cli

# Login to Railway
railway login
```

### Run Migration
```bash
# Link to your Railway project
cd backend
railway link

# Run the migration
railway run alembic upgrade head
```

### Verify Migration
```bash
# Check that migration ran successfully
railway run alembic current

# Should show:
# 005 (head)
```

## Solution 3: Via Railway Dashboard

1. Go to Railway dashboard
2. Open your project
3. Go to the service (backend)
4. Click on "Variables" tab
5. Under "Deployments", click on the latest deployment
6. Click "View Logs"
7. Look for migration output

If migrations didn't run, you can trigger a redeploy:
1. Go to "Deployments" tab
2. Click "Redeploy" on the latest deployment

## Verifying the Fix

After migrations run, you can verify the magic link columns exist:

### Via Debug Endpoint
```bash
curl "https://your-app.up.railway.app/api/debug/magic-link-state?email=your@email.com"
```

Should return:
```json
{
  "email": "your@email.com",
  "has_magic_link_token": true/false,
  "token_hash_preview": "abc123..." or null,
  "magic_link_expires_at": "2024-01-01T12:00:00Z" or null,
  ...
}
```

### Via Database Query (Railway Dashboard)
1. Go to Railway dashboard
2. Click on your Postgres database
3. Click "Query" tab
4. Run:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
  AND column_name LIKE '%magic_link%';
```

Should show:
- magic_link_token (character varying)
- magic_link_expires_at (timestamp with time zone)
- last_magic_link_sent_at (timestamp with time zone)

## Migration File

The migration that adds magic link support is:
- **File**: `alembic/versions/005_authorized_domains_and_auth_fields.py`
- **Revision**: `005`
- **Adds**:
  - `magic_link_token` column to users table
  - `magic_link_expires_at` column to users table
  - `last_magic_link_sent_at` column to users table
  - `authorized_domains` table
  - `authorized_domain_clients` association table

## Troubleshooting

### Migration Fails
If you see an error like "column already exists":
```bash
# Mark migration as complete without running
railway run alembic stamp 005
```

### Check Current Migration Version
```bash
railway run alembic current
```

### View Migration History
```bash
railway run alembic history
```

### Reset and Re-run (⚠️ Caution - Development Only)
```bash
# Downgrade to specific version
railway run alembic downgrade 004

# Then upgrade
railway run alembic upgrade head
```

## After Migration Success

Once migrations complete successfully:
1. Request a new magic link to your email
2. Check the debug endpoint to verify token was saved
3. Click the magic link
4. You should be successfully authenticated!

The server logs will show detailed information about the token generation and verification process.

