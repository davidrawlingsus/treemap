# 🚀 Deployment Success - Railway

## Production URLs

- **Frontend:** https://treemap-production-794d.up.railway.app/
- **Backend API:** https://content-exploration-production-1c75.up.railway.app/
- **Database:** Railway PostgreSQL (internal)

## ✅ What's Deployed

### Frontend (Node.js/Express)
- Serves static files (index.html, assets)
- Dynamic config endpoint (`/config.js`) for environment-aware API URL
- Environment variable: `API_BASE_URL`

### Backend (FastAPI/Python)
- RESTful API for data source management
- Connected to PostgreSQL database
- CORS configured for frontend domain
- Environment variable: `DATABASE_URL`

### Database (PostgreSQL)
- Railway managed PostgreSQL
- JSONB storage for flexible Intercom data
- Sample data already loaded

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway Cloud                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │    Frontend      │      │     Backend      │           │
│  │  Node.js/Express │─────▶│  FastAPI/Python  │           │
│  │   Port: 3000     │      │   Port: 8000     │           │
│  └──────────────────┘      └────────┬─────────┘           │
│                                     │                       │
│                            ┌────────▼─────────┐            │
│                            │   PostgreSQL     │            │
│                            │   Database       │            │
│                            └──────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Frontend Environment Variables
```
API_BASE_URL=https://content-exploration-production-1c75.up.railway.app
```

### Backend Environment Variables
```
DATABASE_URL=postgresql://postgres:...@postgres.railway.internal:5432/railway
```

### Backend CORS Settings
```python
allow_origins=[
    "http://localhost:3000",  # Local development
    "https://treemap-production-794d.up.railway.app",  # Production
]
```

## Local Development

### Start Backend
```bash
cd backend
source venv/bin/activate
./start.sh
```
Backend runs on: http://localhost:8000

### Start Frontend
```bash
npm start
```
Frontend runs on: http://localhost:3000

## Deployment Process

Both services auto-deploy on git push:

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "Your message"
   git push origin master
   ```

2. **Railway auto-deploys:**
   - Detects changes in GitHub
   - Builds and deploys automatically
   - Takes ~2-3 minutes

## API Endpoints

### Health Check
```bash
curl https://content-exploration-production-1c75.up.railway.app/health
```

### List Data Sources
```bash
curl https://content-exploration-production-1c75.up.railway.app/api/data-sources
```

### Get Data Source Details
```bash
curl https://content-exploration-production-1c75.up.railway.app/api/data-sources/{id}
```

### Upload New Data Source (from local machine)
```bash
cd backend
source venv/bin/activate
python upload_sample_data.py
```
(Update the API_BASE_URL in the script to your production URL)

## Troubleshooting

### Frontend shows "Error loading data"
- Check frontend `/config.js` includes `https://` in API_BASE_URL
- Verify backend is running (test `/health` endpoint)
- Check browser console for CORS errors

### CORS Errors
- Ensure backend CORS includes frontend domain
- Redeploy backend after CORS changes

### Backend fails to start
- Check DATABASE_URL is set correctly
- View logs in Railway dashboard
- Verify all dependencies in requirements.txt

### Database connection errors
- Check DATABASE_URL format
- Ensure using internal Railway URL: `postgres.railway.internal`
- Verify database service is running

## Key Files

- `server.js` - Frontend Express server
- `backend/app/main.py` - FastAPI application
- `backend/Procfile` - Railway start command
- `backend/railway.toml` - Railway configuration
- `railway.toml` - Frontend Railway configuration

## Common Issues Solved

1. ✅ **Missing `https://` in API_BASE_URL** - Always include protocol
2. ✅ **CORS blocking requests** - Updated backend allow_origins
3. ✅ **Backend "no start command"** - Added Procfile and railway.toml
4. ✅ **Frontend using localhost** - Set API_BASE_URL environment variable
5. ✅ **JSONB schema mismatch** - Updated Pydantic schemas to accept list or dict

## Next Steps (Phase 2)

When ready to add more features:

1. **Multi-tenancy**
   - Add `clients` table
   - Add `users` table
   - Link data sources to clients

2. **Authentication (Supabase)**
   - Integrate Supabase Auth
   - Add JWT validation in backend
   - Protect API endpoints

3. **AI Insights**
   - Integrate OpenAI GPT-4
   - Generate analysis ideas
   - Add insights UI

4. **Data Source Management UI**
   - Upload interface
   - List/edit/delete data sources
   - Client dashboard

## Support

- **Logs:** Railway Dashboard → Service → Deployments → View Logs
- **Metrics:** Railway Dashboard → Service → Metrics
- **Database:** Railway Dashboard → PostgreSQL service

## Success Metrics

- ✅ Frontend deployed and accessible
- ✅ Backend API deployed and responding
- ✅ Database connected and operational
- ✅ CORS configured correctly
- ✅ Sample data loaded and rendering
- ✅ D3.js treemap visualization working
- ✅ Data source selector functional
- ✅ Local development environment preserved

---

**Deployment Date:** October 28, 2025
**Status:** ✅ Fully Operational
**Phase:** Phase 1 Complete - Basic data flow working

