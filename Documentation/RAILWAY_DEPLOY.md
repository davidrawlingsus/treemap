# Deploying Frontend to Railway

## Prerequisites

1. Railway CLI installed: `npm i -g @railway/cli`
2. Railway account and project created
3. Backend already deployed (to get the API URL)

## Deployment Steps

### 1. Install Dependencies Locally (test first)

```bash
npm install
```

### 2. Test Locally

```bash
# Set your production API URL for testing
export API_BASE_URL=https://your-backend.railway.app
npm start
```

Visit `http://localhost:3000` to verify it works.

### 3. Deploy to Railway

#### Option A: Via Railway CLI

```bash
# Login to Railway
railway login

# Link to your project (or create new)
railway link

# Set the API_BASE_URL environment variable
railway variables set API_BASE_URL=https://your-backend.railway.app

# Deploy
railway up
```

#### Option B: Via Railway Dashboard

1. Go to https://railway.app/dashboard
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `treemap` repository
4. Railway will auto-detect the Node.js app
5. Go to "Variables" tab and add:
   - `API_BASE_URL` = `https://your-backend.railway.app`
6. Railway will automatically deploy

### 4. Get Your Frontend URL

After deployment, Railway will provide a URL like:
```
https://your-frontend.railway.app
```

### 5. Update Backend CORS

Update your backend's CORS settings in `backend/app/main.py` to allow your frontend domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend.railway.app"  # Add this
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy your backend after this change.

## Environment Variables

### Required
- `API_BASE_URL` - Full URL to your backend API (e.g., `https://your-backend.railway.app`)

### Optional
- `PORT` - Port to run on (Railway sets this automatically)

## Verification

After deployment:

1. Visit your frontend URL
2. Open browser console (F12)
3. Check for any CORS errors
4. Verify the data source dropdown loads
5. Select a data source and verify the treemap renders

## Troubleshooting

### CORS Errors
- Make sure backend CORS includes your frontend domain
- Redeploy backend after CORS changes

### "Failed to fetch" errors
- Verify `API_BASE_URL` is set correctly in Railway variables
- Check backend is running and accessible
- Check backend logs in Railway dashboard

### Empty/White Page
- Check browser console for JavaScript errors
- Verify `config.js` is loading (check Network tab)
- Check that `APP_CONFIG.API_BASE_URL` is defined

## Architecture

```
Frontend (Railway)  →  Backend (Railway)  →  PostgreSQL (Railway)
     ↓                      ↓                        ↓
  Node.js/Express    FastAPI/Uvicorn        Railway Postgres
  Serves static      REST API               JSONB storage
  files + config
```

## Notes

- Frontend is served via Express for environment variable injection
- API URL is dynamically loaded via `/config.js` endpoint
- Falls back to `localhost:8000` if config fails (for local dev)
- Railway auto-detects Node.js and runs `npm start`

