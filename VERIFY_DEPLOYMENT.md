# Verify Magic Link Fix - Step by Step

## Current Status

You're seeing: **"No magic link was requested for this email"**

This means the `magic_link_token` column still doesn't exist in the database, which means:
- Railway is still deploying, OR
- The migration failed to run

## Step 1: Check Railway Deployment Status

1. Go to https://railway.app/dashboard
2. Find your backend service
3. Click on "Deployments" tab
4. Look for the latest deployment (commit `dc5c8d7`)
5. Check the status:
   - ⏳ **Building/Deploying**: Wait for it to complete
   - ✅ **Active**: Deployment succeeded - proceed to Step 2
   - ❌ **Failed**: Check logs - see troubleshooting below

## Step 2: Check Migration Logs

**In Railway Dashboard:**
1. Click on your latest deployment
2. Click "View Logs"
3. Look for these messages:

### ✅ SUCCESS - You should see:
```
📦 Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 004 -> 005, add authorized domains and auth fields
✅ Migrations completed successfully
🚀 Starting FastAPI server...
INFO:     Started server process
```

### ❌ FAILURE - If you see:
```
❌ Migration failed! Check logs above
```
Or no migration output at all, see troubleshooting below.

## Step 3: Verify Database Columns Exist

**Option A: Via Debug Endpoint (Easiest)**

Open this URL in your browser:
```
https://vizualizd.marketably.ai/api/debug/magic-link-state?email=david.r@onlinestores.com
```

**Expected Response (Success):**
```json
{
  "email": "david.r@onlinestores.com",
  "has_magic_link_token": false,
  "token_hash_preview": null,
  "magic_link_expires_at": null,
  "last_magic_link_sent_at": null,
  "is_active": true,
  "email_verified_at": null
}
```

If you get this response, the columns exist! ✅

**If you get an error:**
```
500 Internal Server Error - column "magic_link_token" does not exist
```
The migration didn't run. See troubleshooting.

**Option B: Via Railway Database Query**

1. In Railway dashboard, click on your Postgres database
2. Click "Query" tab
3. Run:
```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'users' 
  AND column_name LIKE '%magic_link%';
```

Should return 3 rows:
- magic_link_token
- magic_link_expires_at
- last_magic_link_sent_at

## Step 4: Request a NEW Magic Link

**IMPORTANT:** Any magic links sent BEFORE the migration won't work!

1. Go to https://vizualizd.marketably.ai/
2. Enter your email: `david.r@onlinestores.com`
3. Click "Send Magic Link"
4. Check your email
5. Click the NEW link

## Step 5: Verify It Worked

After clicking the new magic link:

1. Check browser console - should see:
```
Auth check result: true
```

2. Check Railway logs - should see:
```
INFO: Magic link verification attempt for email: david.r@onlinestores.com
INFO: Found user: david.r@onlinestores.com, checking token validity
INFO: Token validation successful for david.r@onlinestores.com
INFO: Successfully verified magic link for david.r@onlinestores.com
INFO: Issued JWT access token for david.r@onlinestores.com
```

3. You should see the client selection screen!

---

## Troubleshooting

### Issue: Migration Didn't Run

**Check if railway_start.sh exists:**
```bash
# In Railway logs, you should see the file being used
# If not, the deployment might not have picked it up
```

**Manual Migration (If Automated Failed):**

1. Install Railway CLI:
```bash
npm install -g @railway/cli
railway login
```

2. Link to your project:
```bash
cd backend
railway link
```

3. Run migration manually:
```bash
railway run alembic upgrade head
```

4. Verify:
```bash
railway run alembic current
# Should show: 005 (head)
```

### Issue: Railway Deployment Failed

**Check the build logs for errors like:**
- Missing dependencies
- Syntax errors
- Permission issues

**Common fixes:**
- Ensure `alembic` is in `requirements.txt`
- Ensure `railway_start.sh` has correct line endings (Unix, not Windows)
- Check that Railway environment variables are set

### Issue: "Command not found: alembic"

This means alembic isn't installed. Check:
1. Is `alembic` in `requirements.txt`?
2. Did Railway install dependencies?

### Issue: Database Connection Failed

Check Railway environment variables:
- `DATABASE_URL` should be set by Railway automatically
- It should start with `postgresql://`

---

## Quick Status Check Script

You can test everything with these URLs:

1. **Health Check:**
   ```
   https://vizualizd.marketably.ai/health
   ```
   Should return: `{"status": "healthy", "database": "connected"}`

2. **Check Columns:**
   ```
   https://vizualizd.marketably.ai/api/debug/magic-link-state?email=david.r@onlinestores.com
   ```
   Should return user info (not 500 error)

3. **Request Magic Link:**
   ```
   POST https://vizualizd.marketably.ai/api/auth/magic-link/request
   Body: {"email": "david.r@onlinestores.com"}
   ```
   Should return: `{"message": "Magic link sent...", "expires_at": "..."}`

If all 3 work, the fix is complete! 🎉

---

## What to Share If Still Broken

If it's still not working after these steps, please share:

1. **Railway deployment logs** (specifically the startup section)
2. **Response from the debug endpoint**
3. **Railway logs when you click the magic link**
4. **Screenshot of Railway deployments page** showing the active deployment

This will help me see exactly what's happening!

