# Visualizd Backend

FastAPI backend for the Visualizd multi-tenant analytics platform.

## Setup

1. **Install dependencies:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
Create a `.env` file with your Railway database URL:
```bash
DATABASE_URL=postgresql://user:password@host:port/database
ENVIRONMENT=development
```

3. **Run migrations:**
```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

4. **Run the server:**
```bash
# Development
uvicorn app.main:app --reload --port 8000

# Or simply
python app/main.py
```

5. **Test the API:**
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## API Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `POST /api/data-sources/upload` - Upload JSON file
- `POST /api/data-sources` - Create data source from JSON payload
- `GET /api/data-sources` - List all data sources
- `GET /api/data-sources/{id}` - Get specific data source with raw_data
- `DELETE /api/data-sources/{id}` - Delete data source

## Database

Using PostgreSQL hosted on Railway with JSONB support for flexible data storage.

