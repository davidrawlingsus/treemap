from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from typing import List, Optional
import json
from uuid import UUID

from app.database import get_db, engine, Base
from app.models import Client, DataSource, DimensionName, GrowthIdea
from app.schemas import (
    ClientCreate, ClientResponse,
    DataSourceCreate, DataSourceResponse, DataSourceDetail,
    QuestionInfo, DataSourceWithQuestions,
    DimensionNameCreate, DimensionNameBatchUpdate, DimensionNameResponse,
    GrowthIdeaCreate, GrowthIdeaUpdate, GrowthIdeaResponse,
    GrowthIdeaGenerateRequest, GrowthIdeaGenerateResponse,
    ClientGrowthIdeasStats, TopicSpecificIdeaRequest
)
from app.transformers import DataTransformer, DataSourceType
from app.services import OpenAIService

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


@app.get("/api/data-sources/{data_source_id}", response_model=DataSourceDetail)
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


@app.delete("/api/data-sources/{data_source_id}")
def delete_data_source(data_source_id: UUID, db: Session = Depends(get_db)):
    """Delete a data source"""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    db.delete(data_source)
    db.commit()
    
    return {"message": "Data source deleted successfully"}


# Client Endpoints
@app.get("/api/clients", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    """List all clients"""
    clients = db.query(Client).order_by(Client.name).all()
    return clients


@app.post("/api/clients", response_model=ClientResponse)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client"""
    try:
        # Check if client with same name or slug already exists
        existing = db.query(Client).filter(
            (Client.name == client.name) | (Client.slug == client.slug)
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Client with this name or slug already exists"
            )
        
        db_client = Client(**client.model_dump())
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        
        return db_client
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clients/{client_id}", response_model=ClientResponse)
def get_client(client_id: UUID, db: Session = Depends(get_db)):
    """Get a specific client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return client


@app.get("/api/clients/{client_id}/sources", response_model=List[DataSourceResponse])
def list_client_sources(client_id: UUID, db: Session = Depends(get_db)):
    """List all data sources for a specific client"""
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    data_sources = db.query(DataSource).filter(
        DataSource.client_id == client_id
    ).options(joinedload(DataSource.client)).all()
    
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


@app.get("/api/data-sources/{data_source_id}/questions", response_model=DataSourceWithQuestions)
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


# Dimension Names Endpoints

@app.get("/api/data-sources/{data_source_id}/dimension-names", response_model=List[DimensionNameResponse])
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


@app.post("/api/data-sources/{data_source_id}/dimension-names", response_model=DimensionNameResponse)
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
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(data_source, 'normalized_data')
    
    db.commit()
    db.refresh(existing)
    return existing


@app.post("/api/data-sources/{data_source_id}/dimension-names/batch", response_model=List[DimensionNameResponse])
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
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(data_source, 'normalized_data')
    
    db.commit()
    
    # Refresh all objects
    for result in results:
        db.refresh(result)
    
    return results


@app.delete("/api/data-sources/{data_source_id}/dimension-names/{ref_key}")
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


# Growth Ideas Endpoints

@app.post("/api/data-sources/{data_source_id}/dimensions/{ref_key}/generate-ideas", 
          response_model=GrowthIdeaGenerateResponse)
async def generate_growth_ideas(
    data_source_id: UUID,
    ref_key: str,
    request: Optional[GrowthIdeaGenerateRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Generate growth ideas for a specific dimension using AI.
    
    Args:
        data_source_id: UUID of the data source
        ref_key: Reference key of the dimension (e.g., "ref_1")
        request: Optional parameters for generation
        db: Database session
    """
    # Get the data source with dimension names
    data_source = db.query(DataSource).options(
        joinedload(DataSource.dimension_names),
        joinedload(DataSource.client)
    ).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    if not data_source.client_id:
        raise HTTPException(
            status_code=400, 
            detail="Data source must be associated with a client to generate ideas"
        )
    
    # Get dimension name if available
    dimension_name = None
    for dn in data_source.dimension_names:
        if dn.ref_key == ref_key:
            dimension_name = dn.custom_name
            break
    
    # Filter normalized data for this dimension
    dimension_data = []
    if data_source.normalized_data:
        for row in data_source.normalized_data:
            if isinstance(row, dict):
                row_ref_key = row.get('metadata', {}).get('ref_key')
                if row_ref_key == ref_key:
                    dimension_data.append(row)
    
    if not dimension_data:
        raise HTTPException(
            status_code=400,
            detail=f"No data found for dimension {ref_key}"
        )
    
    # Initialize OpenAI service
    try:
        openai_service = OpenAIService()
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI service not configured: {str(e)}"
        )
    
    # Generate ideas
    try:
        result = openai_service.generate_ideas(
            dimension_data=dimension_data,
            dimension_name=dimension_name,
            ref_key=ref_key,
            data_source_name=data_source.name
        )
        
        # Store the generated ideas in the database
        created_ideas = []
        for idea_text in result['ideas']:
            growth_idea = GrowthIdea(
                client_id=data_source.client_id,
                data_source_id=data_source_id,
                dimension_ref_key=ref_key,
                dimension_name=dimension_name,
                idea_text=idea_text,
                status="pending",
                context_data=result['context'],
                generation_prompt=result['prompt']
            )
            db.add(growth_idea)
            created_ideas.append(growth_idea)
        
        db.commit()
        
        # Refresh and prepare response
        for idea in created_ideas:
            db.refresh(idea)
        
        response_ideas = []
        for idea in created_ideas:
            response_ideas.append(GrowthIdeaResponse(
                id=idea.id,
                client_id=idea.client_id,
                data_source_id=idea.data_source_id,
                dimension_ref_key=idea.dimension_ref_key,
                dimension_name=idea.dimension_name,
                idea_text=idea.idea_text,
                status=idea.status,
                priority=idea.priority,
                created_at=idea.created_at,
                updated_at=idea.updated_at,
                client_name=data_source.client.name if data_source.client else None,
                data_source_name=data_source.name
            ))
        
        return GrowthIdeaGenerateResponse(
            ideas=response_ideas,
            total_generated=len(response_ideas)
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating ideas: {str(e)}"
        )


@app.post("/api/data-sources/{data_source_id}/dimensions/{ref_key}/generate-topic-ideas", 
          response_model=GrowthIdeaGenerateResponse)
async def generate_topic_specific_ideas(
    data_source_id: UUID,
    ref_key: str,
    request: TopicSpecificIdeaRequest,
    db: Session = Depends(get_db)
):
    """
    Generate growth ideas for a specific topic/category within a dimension using AI.
    
    Args:
        data_source_id: UUID of the data source
        ref_key: Reference key of the dimension (e.g., "ref_1")
        request: Topic-specific parameters for generation
        db: Database session
    """
    # Get the data source with dimension names
    data_source = db.query(DataSource).options(
        joinedload(DataSource.dimension_names),
        joinedload(DataSource.client)
    ).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    if not data_source.client_id:
        raise HTTPException(
            status_code=400, 
            detail="Data source must be associated with a client to generate ideas"
        )
    
    # Get dimension name if available
    dimension_name = None
    for dn in data_source.dimension_names:
        if dn.ref_key == ref_key:
            dimension_name = dn.custom_name
            break
    
    # Filter normalized data for this dimension
    dimension_data = []
    if data_source.normalized_data:
        for row in data_source.normalized_data:
            if isinstance(row, dict):
                row_ref_key = row.get('metadata', {}).get('ref_key')
                if row_ref_key == ref_key:
                    dimension_data.append(row)
    
    if not dimension_data:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for dimension '{ref_key}'"
        )
    
    try:
        # Generate topic-specific ideas using OpenAI
        openai_service = OpenAIService()
        result = openai_service.generate_topic_specific_ideas(
            dimension_data=dimension_data,
            dimension_name=dimension_name,
            ref_key=ref_key,
            data_source_name=data_source.name,
            topic_name=request.topic_name,
            category_name=request.category_name,
            max_ideas=request.max_ideas
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )
        
        # Store ideas in database
        created_ideas = []
        for idea_data in result["ideas"]:
            idea = GrowthIdea(
                client_id=data_source.client_id,
                data_source_id=data_source_id,
                dimension_ref_key=ref_key,
                dimension_name=dimension_name,
                idea_text=idea_data["idea"],
                status="pending",
                priority=idea_data.get("priority", 2),
                context_data=result["context"],
                generation_prompt=result["prompt"]
            )
            db.add(idea)
            created_ideas.append(idea)
        
        db.commit()
        
        # Refresh to get IDs and return response
        for idea in created_ideas:
            db.refresh(idea)
        
        # Convert to response format
        idea_responses = []
        for idea in created_ideas:
            idea_responses.append(GrowthIdeaResponse(
                id=idea.id,
                client_id=idea.client_id,
                data_source_id=idea.data_source_id,
                dimension_ref_key=idea.dimension_ref_key,
                dimension_name=idea.dimension_name,
                idea_text=idea.idea_text,
                status=idea.status,
                priority=idea.priority,
                created_at=idea.created_at,
                updated_at=idea.updated_at,
                client_name=data_source.client.name if data_source.client else None,
                data_source_name=data_source.name
            ))
        
        return GrowthIdeaGenerateResponse(
            ideas=idea_responses,
            total_generated=len(idea_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating topic-specific ideas: {str(e)}"
        )


@app.get("/api/data-sources/{data_source_id}/dimensions/{ref_key}/ideas",
         response_model=List[GrowthIdeaResponse])
def get_dimension_ideas(
    data_source_id: UUID,
    ref_key: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all growth ideas for a specific dimension.
    
    Args:
        data_source_id: UUID of the data source
        ref_key: Reference key of the dimension
        status: Optional filter by status (pending, accepted, rejected)
        db: Database session
    """
    # Verify data source exists
    data_source = db.query(DataSource).options(
        joinedload(DataSource.client)
    ).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Query ideas
    query = db.query(GrowthIdea).filter(
        GrowthIdea.data_source_id == data_source_id,
        GrowthIdea.dimension_ref_key == ref_key
    )
    
    if status:
        query = query.filter(GrowthIdea.status == status)
    
    ideas = query.order_by(GrowthIdea.created_at.desc()).all()
    
    # Build response
    response = []
    for idea in ideas:
        response.append(GrowthIdeaResponse(
            id=idea.id,
            client_id=idea.client_id,
            data_source_id=idea.data_source_id,
            dimension_ref_key=idea.dimension_ref_key,
            dimension_name=idea.dimension_name,
            idea_text=idea.idea_text,
            status=idea.status,
            priority=idea.priority,
            created_at=idea.created_at,
            updated_at=idea.updated_at,
            client_name=data_source.client.name if data_source.client else None,
            data_source_name=data_source.name
        ))
    
    return response


@app.patch("/api/growth-ideas/{idea_id}", response_model=GrowthIdeaResponse)
def update_growth_idea(
    idea_id: UUID,
    update_data: GrowthIdeaUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a growth idea's status or priority.
    
    Args:
        idea_id: UUID of the idea
        update_data: Update data (status and/or priority)
        db: Database session
    """
    idea = db.query(GrowthIdea).options(
        joinedload(GrowthIdea.client),
        joinedload(GrowthIdea.data_source)
    ).filter(GrowthIdea.id == idea_id).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Growth idea not found")
    
    # Update fields
    if update_data.status is not None:
        if update_data.status not in ["pending", "accepted", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'pending', 'accepted', or 'rejected'"
            )
        idea.status = update_data.status
    
    if update_data.priority is not None:
        idea.priority = update_data.priority
    
    db.commit()
    db.refresh(idea)
    
    return GrowthIdeaResponse(
        id=idea.id,
        client_id=idea.client_id,
        data_source_id=idea.data_source_id,
        dimension_ref_key=idea.dimension_ref_key,
        dimension_name=idea.dimension_name,
        idea_text=idea.idea_text,
        status=idea.status,
        priority=idea.priority,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
        client_name=idea.client.name if idea.client else None,
        data_source_name=idea.data_source.name if idea.data_source else None
    )


@app.delete("/api/growth-ideas/{idea_id}")
def delete_growth_idea(idea_id: UUID, db: Session = Depends(get_db)):
    """Delete a growth idea"""
    idea = db.query(GrowthIdea).filter(GrowthIdea.id == idea_id).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Growth idea not found")
    
    db.delete(idea)
    db.commit()
    
    return {"message": "Growth idea deleted successfully"}


@app.get("/api/clients/{client_id}/growth-ideas", response_model=List[GrowthIdeaResponse])
def get_client_growth_ideas(
    client_id: UUID,
    status: Optional[str] = None,
    data_source_id: Optional[UUID] = None,
    sort_by: Optional[str] = "date",  # date, priority
    db: Session = Depends(get_db)
):
    """
    Get all growth ideas for a client with optional filtering and sorting.
    
    Args:
        client_id: UUID of the client
        status: Optional filter by status
        data_source_id: Optional filter by data source
        sort_by: Sort order (date or priority)
        db: Database session
    """
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Query ideas
    query = db.query(GrowthIdea).options(
        joinedload(GrowthIdea.data_source)
    ).filter(GrowthIdea.client_id == client_id)
    
    if status:
        query = query.filter(GrowthIdea.status == status)
    
    if data_source_id:
        query = query.filter(GrowthIdea.data_source_id == data_source_id)
    
    # Apply sorting
    if sort_by == "priority":
        query = query.order_by(
            GrowthIdea.priority.asc().nullslast(),
            GrowthIdea.created_at.desc()
        )
    else:  # default to date
        query = query.order_by(GrowthIdea.created_at.desc())
    
    ideas = query.all()
    
    # Build response
    response = []
    for idea in ideas:
        response.append(GrowthIdeaResponse(
            id=idea.id,
            client_id=idea.client_id,
            data_source_id=idea.data_source_id,
            dimension_ref_key=idea.dimension_ref_key,
            dimension_name=idea.dimension_name,
            idea_text=idea.idea_text,
            status=idea.status,
            priority=idea.priority,
            created_at=idea.created_at,
            updated_at=idea.updated_at,
            client_name=client.name,
            data_source_name=idea.data_source.name if idea.data_source else None
        ))
    
    return response


@app.get("/api/clients/{client_id}/growth-ideas/stats", response_model=ClientGrowthIdeasStats)
def get_client_growth_ideas_stats(client_id: UUID, db: Session = Depends(get_db)):
    """
    Get statistics for a client's growth ideas.
    
    Args:
        client_id: UUID of the client
        db: Database session
    """
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get all ideas for this client
    ideas = db.query(GrowthIdea).options(
        joinedload(GrowthIdea.data_source)
    ).filter(GrowthIdea.client_id == client_id).all()
    
    # Calculate statistics
    total_ideas = len(ideas)
    accepted_count = sum(1 for idea in ideas if idea.status == "accepted")
    pending_count = sum(1 for idea in ideas if idea.status == "pending")
    rejected_count = sum(1 for idea in ideas if idea.status == "rejected")
    
    # Group by data source
    by_data_source = {}
    for idea in ideas:
        ds_name = idea.data_source.name if idea.data_source else "Unknown"
        by_data_source[ds_name] = by_data_source.get(ds_name, 0) + 1
    
    # Group by priority
    by_priority = {
        "high": sum(1 for idea in ideas if idea.priority == 1),
        "medium": sum(1 for idea in ideas if idea.priority == 2),
        "low": sum(1 for idea in ideas if idea.priority == 3),
        "none": sum(1 for idea in ideas if idea.priority is None)
    }
    
    return ClientGrowthIdeasStats(
        total_ideas=total_ideas,
        accepted_count=accepted_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        by_data_source=by_data_source,
        by_priority=by_priority
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

