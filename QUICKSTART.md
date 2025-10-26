# Quick Start Guide

## Running the Application

### 1. Start the Backend (Terminal 1)

```bash
cd backend
source venv/bin/activate
./start.sh
```

The API will be available at `http://localhost:8000`

### 2. Start the Frontend (Terminal 2)

```bash
# From the treemap root directory
./serve.sh
```

Or manually:
```bash
python3 -m http.server 3000
```

The frontend will be available at `http://localhost:3000`

### 3. Open in Browser

Visit: `http://localhost:3000/index.html`

Or run:
```bash
open http://localhost:3000/index.html
```

## Important Notes

⚠️ **Don't open `index.html` directly** - Opening the file with `file://` protocol will cause CORS errors. Always serve it through HTTP on port 3000.

## Current Running Servers

If everything is running correctly, you should have:
- ✅ Backend API: `http://localhost:8000`
- ✅ Frontend: `http://localhost:3000`

## Stopping the Servers

**Backend:**
- Press `CTRL+C` in the backend terminal

**Frontend:**
- Press `CTRL+C` in the frontend terminal

Or kill both:
```bash
# Kill backend
lsof -ti:8000 | xargs kill -9

# Kill frontend
lsof -ti:3000 | xargs kill -9
```

## Uploading New Data

While servers are running:

```bash
cd backend
source venv/bin/activate
python upload_sample_data.py
```

Or use the API directly:
```bash
curl -X POST "http://localhost:8000/api/data-sources/upload" \
  -F "file=@your-data.json" \
  -F "name=My Data Source Name"
```

## Verifying Everything Works

1. **Check Backend Health:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy","database":"connected"}`

2. **Check Data Sources:**
   ```bash
   curl http://localhost:8000/api/data-sources
   ```
   Should return an array of your data sources

3. **Open Frontend:**
   Visit `http://localhost:3000/index.html` and you should see:
   - Data source dropdown populated
   - Treemap visualization rendering
   - Interactive charts below

## Troubleshooting

**"Error loading data: Failed to fetch"**
- Make sure you're accessing via `http://localhost:3000/index.html` (not `file://`)
- Check backend is running: `curl http://localhost:8000/health`
- Check browser console (F12) for detailed errors

**"No data sources available"**
- Upload data using `python upload_sample_data.py`
- Verify data in database: `curl http://localhost:8000/api/data-sources`

**Port already in use**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Find and kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

## API Documentation

Interactive API docs: `http://localhost:8000/docs`

