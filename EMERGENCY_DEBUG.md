# EMERGENCY DEBUG - Magic Link Not Working

## Step 1: Check Database Columns (CRITICAL)

Open this URL in your browser RIGHT NOW:

```
https://vizualizd.marketably.ai/api/debug/magic-link-state?email=david.r@onlinestores.com
```

### Expected Results:

**✅ IF COLUMNS EXIST** (migration ran):
```json
{
  "email": "david.r@onlinestores.com",
  "has_magic_link_token": false,
  "token_hash_preview": null,
  "magic_link_expires_at": null,
  ...
}
```

**❌ IF COLUMNS DON'T EXIST** (migration didn't run):
```
500 Internal Server Error
column "magic_link_token" does not exist
```

## Step 2A: IF COLUMNS EXIST

The migration worked! The issue is the token isn't being saved. Let's debug:

1. **Request a BRAND NEW magic link**:
   - Go to https://vizualizd.marketably.ai/
   - Clear browser cache (Cmd+Shift+Delete)
   - Enter your email
   - Click "Send Magic Link"

2. **Check the debug endpoint IMMEDIATELY after requesting**:
   ```
   https://vizualizd.marketably.ai/api/debug/magic-link-state?email=david.r@onlinestores.com
   ```
   
   **Should now show:**
   ```json
   {
     "has_magic_link_token": true,  ← Should be TRUE now!
     "token_hash_preview": "abc123...",
     "magic_link_expires_at": "2024-11-15T...",
     ...
   }
   ```

3. **If still FALSE**: Token generation is failing. Share Railway logs showing the magic link request.

4. **If TRUE**: Click the magic link in your email and it should work!

## Step 2B: IF COLUMNS DON'T EXIST

**The migration didn't run!** Here's how to fix it:

### Check Railway Deployment Logs

1. Go to Railway Dashboard
2. Click on your backend service
3. Click "Deployments"
4. Click on the LATEST deployment (commit `d240b9b`)
5. Click "View Logs"

**Look for:**
```
📦 Running database migrations...
INFO  [alembic.runtime.migration] Running upgrade 004 -> 005
✅ Migrations completed successfully
```

### If You DON'T See This:

The startup script isn't running. Manually run the migration:

**Option A: Via Railway CLI** (Fastest)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
cd backend
railway link

# Run migration
railway run alembic upgrade head

# Verify
railway run alembic current
# Should show: 005 (head)
```

**Option B: Via Railway Dashboard**

1. Go to Railway dashboard
2. Click on your database (Postgres)
3. Click "Connect"
4. Copy the DATABASE_URL
5. On your local machine:
```bash
cd backend
export DATABASE_URL="<paste-url-here>"
alembic upgrade head
```

## Step 3: Verify & Test

After migration completes:

1. **Check columns exist** (Step 1 URL should work)
2. **Request NEW magic link**
3. **Check debug endpoint** (should show `has_magic_link_token: true`)
4. **Click magic link**
5. **Success!** 🎉

## Quick Diagnostic Commands

### Check if Railway deployment is running the script:

In Railway logs, search for:
- `railway_start.sh` or `Running database migrations`

### Check Alembic version on Railway:

```bash
railway run alembic current
```

Should show: `005 (head)`

If it shows `004` or less, migrations haven't run.

---

## What to Share If Still Broken

Please share:

1. **Result from debug endpoint** (the JSON or error)
2. **Railway logs** (specifically the startup section showing migrations)
3. **Output of**: `railway run alembic current`
4. **Are you clicking a NEW link or OLD link?** (Must be NEW after deployment)

This will tell me exactly what's happening!

