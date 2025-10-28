from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import json
from uuid import UUID

from app.database import get_db, engine, Base
from app.models import DataSource
from app.schemas import DataSourceCreate, DataSourceResponse, DataSourceDetail
from app.transformers import DataTransformer, DataSourceType

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Visualizd API", version="0.1.0")

# CORS configuration - allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://treemap-production-794d.up.railway.app",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Visualizd API", "version": "0.1.0"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check if API and database are working"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/api/data-sources/upload", response_model=DataSourceResponse)
async def upload_data_source(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    source_type: Optional[str] = Form(None),
    auto_detect: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Upload a JSON file as a data source.
    
    Args:
        file: JSON file to upload
        name: Optional name for the data source (defaults to filename)
        source_type: Optional source format type (will auto-detect if not provided)
        auto_detect: Whether to auto-detect the format (default: True)
        db: Database session
    """
    try:
        # Read the uploaded file
        contents = await file.read()
        raw_data = json.loads(contents)
        
        # Validate that raw_data is a list
        if not isinstance(raw_data, list):
            raise HTTPException(
                status_code=400, 
                detail="JSON data must be an array of objects"
            )
        
        # Use filename as name if not provided
        if not name:
            name = file.filename.replace('.json', '')
        
        # Detect or use provided source type
        detected_format = None
        if auto_detect:
            detected_format = DataTransformer.detect_format(raw_data)
            print(f"Auto-detected format: {detected_format}")
        elif source_type:
            try:
                detected_format = DataSourceType(source_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source_type. Must be one of: {[t.value for t in DataSourceType]}"
                )
        else:
            detected_format = DataSourceType.GENERIC
        
        # Transform data to normalized format
        normalized_data = DataTransformer.transform(raw_data, detected_format)
        
        print(f"Transformed {len(raw_data)} raw rows into {len(normalized_data)} normalized rows")
        
        # Create data source
        data_source = DataSource(
            name=name,
            source_type=source_type or "generic",
            source_format=detected_format.value,
            raw_data=raw_data,
            normalized_data=normalized_data,
            is_normalized=True
        )
        
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        
        return data_source
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        db.rollback()
        print(f"Error uploading data source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data-sources", response_model=DataSourceResponse)
def create_data_source(data: DataSourceCreate, db: Session = Depends(get_db)):
    """Create a data source from JSON payload"""
    try:
        data_source = DataSource(
            name=data.name,
            source_type=data.source_type,
            raw_data=data.raw_data
        )
        
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        
        return data_source
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-sources", response_model=List[DataSourceResponse])
def list_data_sources(db: Session = Depends(get_db)):
    """List all data sources (without raw_data)"""
    data_sources = db.query(DataSource).all()
    return data_sources


@app.get("/api/data-sources/{data_source_id}", response_model=DataSourceDetail)
def get_data_source(data_source_id: UUID, use_raw: bool = False, db: Session = Depends(get_db)):
    """
    Get a specific data source with full data.
    
    Args:
        data_source_id: UUID of the data source
        use_raw: If True, return raw_data; if False, return normalized_data (default)
        db: Database session
    """
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Return the appropriate data format
    # The response model will handle serialization
    return data_source


@app.delete("/api/data-sources/{data_source_id}")
def delete_data_source(data_source_id: UUID, db: Session = Depends(get_db)):
    """Delete a data source"""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    db.delete(data_source)
    db.commit()
    
    return {"message": "Data source deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

