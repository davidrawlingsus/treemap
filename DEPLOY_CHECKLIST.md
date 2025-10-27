# Railway Deployment Checklist

## ✅ Pre-Deployment (Completed)

- [x] Created `package.json` with Express server
- [x] Created `server.js` to serve static files
- [x] Updated `index.html` to use dynamic API URL
- [x] Added `railway.toml` configuration
- [x] Added `.gitignore` for Node.js
- [x] Tested locally - frontend works with backend

## 🚀 Deploy Frontend to Railway

### Step 1: Via Railway Dashboard (Recommended)

1. Go to https://railway.app/dashboard
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `treemap` repository (or fork it first)
4. Railway will auto-detect the Node.js app from `package.json`
5. Click **"Deploy"**

### Step 2: Set Environment Variables

In your Railway frontend project:

1. Go to **"Variables"** tab
2. Click **"New Variable"**
3. Add:
   ```
   Name:  API_BASE_URL
   Value: https://your-backend-url.railway.app
   ```
   (Replace with your actual backend Railway URL)

### Step 3: Get Your Frontend URL

After deployment completes:
- Railway will provide a URL like: `https://treemap-production-xxxx.up.railway.app`
- Copy this URL

### Step 4: Update Backend CORS

You need to allow your frontend domain in the backend:

1. Go to `backend/app/main.py`
2. Update the CORS middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Keep for local dev
        "https://treemap-production-xxxx.up.railway.app"  # Add your frontend URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. Commit and push the changes
4. Railway will auto-deploy the backend update

### Step 5: Verify

1. Visit your frontend URL
2. Open browser DevTools (F12) → Console
3. You should see:
   - ✅ Data sources loading
   - ✅ Treemap rendering
   - ❌ No CORS errors

## 🐛 Troubleshooting

### Issue: "Failed to fetch" or CORS errors
**Fix:** Make sure backend CORS includes your frontend URL

### Issue: Blank page
**Fix:** Check browser console for errors, verify `/config.js` loads

### Issue: Backend connection refused
**Fix:** Verify `API_BASE_URL` environment variable is set correctly in Railway

## 📝 Notes

- Both frontend and backend can be in separate Railway projects
- Or both can be in the same Railway project (different services)
- Frontend uses Node.js/Express for environment variable injection
- Backend needs to allow frontend domain in CORS
- Railway auto-deploys on git push

## Alternative: CLI Deployment

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Set environment variable
railway variables set API_BASE_URL=https://your-backend.railway.app

# Deploy
railway up
```

## Current Status

- ✅ Frontend ready for deployment
- ✅ Tested locally with backend
- ⏳ Waiting for Railway deployment
- ⏳ Need to update backend CORS after frontend URL is known

