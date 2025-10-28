# Debugging Railway Deployment

## Issue: "Error loading data sources"

This means the frontend can't connect to the backend API.

## Step-by-Step Diagnosis

### 1. Check Frontend Environment Variable

In your Railway **frontend** project:

1. Go to **Variables** tab
2. Look for `API_BASE_URL`
3. It should be: `https://your-backend-name.railway.app` (NOT localhost!)

**If it's missing or wrong:**
- Click "New Variable"
- Name: `API_BASE_URL`
- Value: Your backend Railway URL (see step 2)

### 2. Get Your Backend URL

Your backend needs to be deployed to Railway first!

**Check if backend is deployed:**
1. Go to Railway Dashboard
2. Look for your backend project (with FastAPI/Python)
3. Click on it → Go to "Settings" → Copy the public URL

**If backend is NOT deployed yet:**
You need to deploy the backend first! Options:

#### Option A: Deploy Backend via Railway Dashboard
1. New Project → Deploy from GitHub
2. Select your repo
3. Railway detects Python app in `backend/` folder
4. Add environment variable:
   - Name: `DATABASE_URL`
   - Value: (your Railway Postgres connection string)
5. Railway will deploy

#### Option B: Deploy Backend via CLI
```bash
cd backend
railway login
railway link
railway up
```

### 3. Check Backend is Running

Once backend is deployed, test it:

```bash
# Replace with your actual backend URL
curl https://your-backend.railway.app/health
```

Expected response:
```json
{"status":"healthy","database":"connected"}
```

### 4. Update Backend CORS

Your backend needs to allow requests from your frontend domain!

Edit `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local dev
        "https://your-frontend.railway.app"  # ADD THIS!
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then commit and push (Railway auto-deploys).

### 5. Check Browser Console

Open your Railway frontend in browser:
1. Press F12 (DevTools)
2. Go to Console tab
3. Look for errors

**Common errors:**

#### "Failed to fetch"
- Backend not deployed or URL wrong
- Check `API_BASE_URL` in Railway variables

#### "CORS policy blocked"
- Backend CORS doesn't include frontend domain
- Update CORS in `backend/app/main.py`

#### "net::ERR_NAME_NOT_RESOLVED"
- Backend URL is incorrect or doesn't exist
- Verify backend deployment

### 6. Test Config Endpoint

Visit: `https://your-frontend.railway.app/config.js`

You should see:
```javascript
window.APP_CONFIG = { API_BASE_URL: 'https://your-backend.railway.app' };
```

**If you see localhost:**
- `API_BASE_URL` environment variable is NOT set in Railway
- Go to frontend Variables tab and add it

## Quick Checklist

- [ ] Backend is deployed to Railway
- [ ] Backend health check works: `/health` returns 200
- [ ] Frontend has `API_BASE_URL` environment variable set
- [ ] Backend CORS includes frontend domain
- [ ] `/config.js` shows correct backend URL (not localhost)

## Common Mistakes

❌ Backend still running locally (not deployed to Railway)
❌ `API_BASE_URL` not set or set to localhost
❌ CORS not updated to include frontend domain
❌ Using HTTP instead of HTTPS for Railway URLs
❌ Backend environment variable `DATABASE_URL` not set

## Need Help?

Run these commands and share the output:

```bash
# Check what your frontend's config.js returns
curl https://your-frontend.railway.app/config.js

# Check if backend is reachable
curl https://your-backend.railway.app/health

# Check CORS
curl -i -X OPTIONS https://your-backend.railway.app/api/data-sources \
  -H "Origin: https://your-frontend.railway.app" \
  -H "Access-Control-Request-Method: GET"
```

