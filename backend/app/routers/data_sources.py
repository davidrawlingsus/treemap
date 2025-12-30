"""
Data source management routes.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified
from uuid import UUID
from typing import List, Optional
import logging

from app.database import get_db
from app.models import DataSource, DimensionName
from app.schemas import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceDetail,
    DataSourceWithQuestions,
    DimensionNameCreate,
    DimensionNameResponse,
    DimensionNameBatchUpdate,
)
from app.transformers import DataTransformer, DataSourceType

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])
logger = logging.getLogger(__name__)


def enrich_data_with_dimension_names(data: list, dimension_names_map: dict) -> list:
    """
    Enrich normalized data with dimension names from the map.
    Adds dimension_name to metadata for LLM context.
    """
    if not data:
        return data
    
    enriched = []
    for row in data:
        if isinstance(row, dict):
            ref_key = row.get('metadata', {}).get('ref_key')
            if ref_key and ref_key in dimension_names_map:
                if 'metadata' not in row:
                    row['metadata'] = {}
                row['metadata']['dimension_name'] = dimension_names_map[ref_key]
        enriched.append(row)
    
    return enriched


@router.post("/upload", response_model=DataSourceResponse)
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


@router.post("", response_model=DataSourceResponse)
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


@router.get("", response_model=List[DataSourceResponse])
def list_data_sources(
    client_id: Optional[UUID] = None,
    source_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all data sources (without raw_data), with optional filtering"""
    query = db.query(DataSource).options(joinedload(DataSource.client))
    
    if client_id:
        query = query.filter(DataSource.client_id == client_id)
    if source_name:
        query = query.filter(DataSource.source_name == source_name)
    
    data_sources = query.all()
    
    # Add client_name to response
    result = []
    for ds in data_sources:
        ds_dict = {
            'id': ds.id,
            'name': ds.name,
            'client_id': ds.client_id,
            'source_name': ds.source_name,
            'source_type': ds.source_type,
            'source_format': ds.source_format,
            'is_normalized': ds.is_normalized,
            'created_at': ds.created_at,
            'updated_at': ds.updated_at,
            'client_name': ds.client.name if ds.client else None
        }
        result.append(ds_dict)
    
    return result


@router.get("/{data_source_id}", response_model=DataSourceDetail)
def get_data_source(data_source_id: UUID, use_raw: bool = False, db: Session = Depends(get_db)):
    """
    Get a specific data source with full data.
    Enriches the data with dimension names for LLM context.
    
    Args:
        data_source_id: UUID of the data source
        use_raw: If True, return raw_data; if False, return normalized_data (default)
        db: Database session
    """
    data_source = db.query(DataSource).options(
        joinedload(DataSource.dimension_names)
    ).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Build dimension names map
    dimension_map = {dn.ref_key: dn.custom_name for dn in data_source.dimension_names}
    
    # Enrich data with dimension names for LLM context
    if data_source.normalized_data and dimension_map:
        data_source.normalized_data = enrich_data_with_dimension_names(
            data_source.normalized_data, 
            dimension_map
        )
    
    # Return the appropriate data format
    # The response model will handle serialization
    return data_source


@router.delete("/{data_source_id}")
def delete_data_source(data_source_id: UUID, db: Session = Depends(get_db)):
    """Delete a data source"""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    db.delete(data_source)
    db.commit()
    
    return {"message": "Data source deleted successfully"}


@router.get("/{data_source_id}/questions", response_model=DataSourceWithQuestions)
def get_data_source_questions(data_source_id: UUID, db: Session = Depends(get_db)):
    """
    Get available questions for a data source.
    Detects ref_* fields that contain objects with 'text' and 'topics' fields.
    Includes custom dimension names if assigned.
    """
    data_source = db.query(DataSource).options(
        joinedload(DataSource.client),
        joinedload(DataSource.dimension_names)
    ).filter(
        DataSource.id == data_source_id
    ).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Build a map of ref_key -> custom_name from dimension_names
    dimension_name_map = {
        dn.ref_key: dn.custom_name 
        for dn in data_source.dimension_names
    }
    
    # Detect questions from normalized_data
    questions = []
    data = data_source.normalized_data if data_source.normalized_data else data_source.raw_data
    
    if data and isinstance(data, list) and len(data) > 0:
        # Look for ref_key in metadata (normalized format)
        question_refs = {}
        
        for row in data[:min(100, len(data))]:
            if not isinstance(row, dict):
                continue
            
            # Check for normalized format with metadata.ref_key
            if 'metadata' in row and isinstance(row['metadata'], dict):
                ref_key = row['metadata'].get('ref_key')
                if ref_key and ref_key not in question_refs:
                    question_refs[ref_key] = {
                        'ref_key': ref_key,
                        'sample_text': row.get('text', '')[:100],  # First 100 chars
                        'response_count': 0,
                        'custom_name': dimension_name_map.get(ref_key)
                    }
            # Also check for raw format with ref_* keys
            else:
                for key, value in row.items():
                    if key.startswith('ref_') and isinstance(value, dict):
                        if 'text' in value and 'topics' in value:
                            if key not in question_refs:
                                question_refs[key] = {
                                    'ref_key': key,
                                    'sample_text': value.get('text', '')[:100],
                                    'response_count': 0,
                                    'custom_name': dimension_name_map.get(key)
                                }
        
        # Count responses for each question
        for row in data:
            if not isinstance(row, dict):
                continue
                
            # Count in normalized format
            if 'metadata' in row and isinstance(row['metadata'], dict):
                ref_key = row['metadata'].get('ref_key')
                if ref_key in question_refs:
                    question_refs[ref_key]['response_count'] += 1
            # Count in raw format
            else:
                for key in question_refs.keys():
                    if key in row and isinstance(row[key], dict) and 'text' in row[key]:
                        question_refs[key]['response_count'] += 1
        
        questions = list(question_refs.values())
    
    # Build response
    result = {
        'id': data_source.id,
        'name': data_source.name,
        'client_id': data_source.client_id,
        'source_name': data_source.source_name,
        'source_type': data_source.source_type,
        'source_format': data_source.source_format,
        'is_normalized': data_source.is_normalized,
        'created_at': data_source.created_at,
        'updated_at': data_source.updated_at,
        'client_name': data_source.client.name if data_source.client else None,
        'questions': questions
    }
    
    return result


@router.get("/{data_source_id}/dimension-names", response_model=List[DimensionNameResponse])
def get_dimension_names(data_source_id: UUID, db: Session = Depends(get_db)):
    """
    Get all custom dimension names for a data source.
    """
    # Verify data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    dimension_names = db.query(DimensionName).filter(
        DimensionName.data_source_id == data_source_id
    ).all()
    
    return dimension_names


@router.post("/{data_source_id}/dimension-names", response_model=DimensionNameResponse)
def create_or_update_dimension_name(
    data_source_id: UUID,
    dimension_data: DimensionNameCreate,
    db: Session = Depends(get_db)
):
    """
    Create or update a single dimension name for a data source.
    Also enriches the normalized_data JSON with the dimension name for LLM context.
    """
    # Verify data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Check if dimension name already exists
    existing = db.query(DimensionName).filter(
        DimensionName.data_source_id == data_source_id,
        DimensionName.ref_key == dimension_data.ref_key
    ).first()
    
    if existing:
        # Update existing
        existing.custom_name = dimension_data.custom_name
    else:
        # Create new
        existing = DimensionName(
            data_source_id=data_source_id,
            ref_key=dimension_data.ref_key,
            custom_name=dimension_data.custom_name
        )
        db.add(existing)
    
    # ENRICH THE JSON: Update normalized_data to include dimension name
    if data_source.normalized_data:
        for row in data_source.normalized_data:
            if isinstance(row, dict) and row.get('metadata', {}).get('ref_key') == dimension_data.ref_key:
                # Add dimension_name to metadata
                if 'metadata' not in row:
                    row['metadata'] = {}
                row['metadata']['dimension_name'] = dimension_data.custom_name
        
        # Mark the column as modified so SQLAlchemy knows to update it
        flag_modified(data_source, 'normalized_data')
    
    db.commit()
    db.refresh(existing)
    return existing


@router.post("/{data_source_id}/dimension-names/batch", response_model=List[DimensionNameResponse])
def batch_update_dimension_names(
    data_source_id: UUID,
    batch_data: DimensionNameBatchUpdate,
    db: Session = Depends(get_db)
):
    """
    Batch create or update multiple dimension names for a data source.
    Also enriches the normalized_data JSON with dimension names for LLM context.
    """
    # Verify data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    results = []
    
    # Build a map of ref_key -> custom_name
    dimension_map = {d.ref_key: d.custom_name for d in batch_data.dimension_names}
    
    for dimension_data in batch_data.dimension_names:
        # Check if dimension name already exists
        existing = db.query(DimensionName).filter(
            DimensionName.data_source_id == data_source_id,
            DimensionName.ref_key == dimension_data.ref_key
        ).first()
        
        if existing:
            # Update existing
            existing.custom_name = dimension_data.custom_name
            results.append(existing)
        else:
            # Create new
            new_dimension_name = DimensionName(
                data_source_id=data_source_id,
                ref_key=dimension_data.ref_key,
                custom_name=dimension_data.custom_name
            )
            db.add(new_dimension_name)
            results.append(new_dimension_name)
    
    # ENRICH THE JSON: Update normalized_data to include all dimension names
    if data_source.normalized_data:
        for row in data_source.normalized_data:
            if isinstance(row, dict):
                ref_key = row.get('metadata', {}).get('ref_key')
                if ref_key and ref_key in dimension_map:
                    # Add dimension_name to metadata
                    if 'metadata' not in row:
                        row['metadata'] = {}
                    row['metadata']['dimension_name'] = dimension_map[ref_key]
        
        # Mark the column as modified so SQLAlchemy knows to update it
        flag_modified(data_source, 'normalized_data')
    
    db.commit()
    
    # Refresh all objects
    for result in results:
        db.refresh(result)
    
    return results


@router.delete("/{data_source_id}/dimension-names/{ref_key}")
def delete_dimension_name(
    data_source_id: UUID,
    ref_key: str,
    db: Session = Depends(get_db)
):
    """
    Delete a custom dimension name.
    """
    dimension_name = db.query(DimensionName).filter(
        DimensionName.data_source_id == data_source_id,
        DimensionName.ref_key == ref_key
    ).first()
    
    if not dimension_name:
        raise HTTPException(status_code=404, detail="Dimension name not found")
    
    db.delete(dimension_name)
    db.commit()
    
    return {"message": "Dimension name deleted successfully"}

