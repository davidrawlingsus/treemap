from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, func
from typing import List, Optional
import json
import os
from uuid import UUID
from pathlib import Path

from app.database import get_db, engine, Base
from app.models import Client, DataSource, DimensionName, User, Membership
from app.schemas import (
    ClientCreate, ClientResponse,
    DataSourceCreate, DataSourceResponse, DataSourceDetail,
    QuestionInfo, DataSourceWithQuestions,
    DimensionNameCreate, DimensionNameBatchUpdate, DimensionNameResponse,
    Token, UserLogin, UserResponse, UserWithClients
)
from app.transformers import DataTransformer, DataSourceType
from app.config import get_settings
from app.auth import (
    get_current_user, get_current_active_founder,
    create_access_token, verify_password
)
from datetime import timedelta

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Visualizd API", version="0.1.0")

# CORS configuration - allow frontend to communicate with backend
# Allow all Railway origins (they use *.up.railway.app pattern) for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*\.(up\.railway\.app|localhost)(:\d+)?$",  # Allow all Railway URLs and localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the parent directory (where index.html is)
# This allows accessing the frontend at http://localhost:8000/index.html
frontend_path = Path(__file__).parent.parent.parent
if (frontend_path / "index.html").exists():
    @app.get("/", response_class=FileResponse)
    def serve_index():
        """Serve the frontend index.html"""
        return FileResponse(frontend_path / "index.html")
    
    @app.get("/index.html", response_class=FileResponse)
    def serve_index_html():
        """Serve the frontend index.html"""
        return FileResponse(frontend_path / "index.html")
    
    # Serve config.js dynamically
    @app.get("/config.js")
    def serve_config():
        """Serve dynamic config.js with API URL"""
        from fastapi.responses import Response
        api_url = "http://localhost:8000"
        config_content = f"window.APP_CONFIG = {{ API_BASE_URL: '{api_url}' }};"
        return Response(content=config_content, media_type="application/javascript")

@app.get("/api")
def api_info():
    """API information endpoint"""
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


# Authentication Endpoints
@app.post("/api/auth/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint - validates email and returns JWT token.
    
    NOTE: For now, this accepts any email from the users table without password validation.
    Password fields may not exist in the Railway database yet.
    """
    settings = get_settings()
    
    # Determine if we're in production (for debug messages)
    # Default to showing debug info unless explicitly in production
    env_check = os.getenv("ENVIRONMENT", "").lower()
    railway_env_check = os.getenv("RAILWAY_ENVIRONMENT", "").lower()
    service_name_check = os.getenv("RAILWAY_SERVICE_NAME", "").lower()
    
    # Only hide debug if explicitly production
    is_production = (
        env_check == "production" or
        railway_env_check == "production" or
        "production" in service_name_check
    )
    
    # Log environment info for debugging (only in non-prod)
    if not is_production:
        print(f"Login attempt - ENV: {env_check}, RAILWAY_ENV: {railway_env_check}, SERVICE: {service_name_check}, is_production: {is_production}")
    
    # Normalize email input
    email_input = credentials.email.strip().lower()
    searched_email = credentials.email.strip()
    
    # Log the search attempt
    if not is_production:
        print(f"Login attempt for email: '{searched_email}' (normalized: '{email_input}')")
    
    # Try case-insensitive email lookup
    try:
        user = db.query(User).filter(
            func.lower(User.email) == email_input
        ).first()
        
        # If not found, try ilike as fallback
        if not user:
            if not is_production:
                print(f"  First lookup failed, trying ilike...")
            user = db.query(User).filter(
                User.email.ilike(f"%{email_input}%")
            ).first()
        
        if user and not is_production:
            print(f"  User found: {user.email} (active: {user.is_active}, founder: {user.is_founder})")
        elif not user and not is_production:
            print(f"  User not found after both lookup attempts")
            
    except Exception as e:
        # Database error - show helpful message
        print(f"  Database error: {e}")
        import traceback
        traceback.print_exc()
        if not is_production:
            raise HTTPException(
                status_code=500,
                detail=f"Database error during login: {str(e)}"
            )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
    
    if not user:
        # Helpful debugging: list available emails in dev (don't expose in production)
        # Always show debug info unless explicitly in production
        try:
            all_users = db.query(User).all()
            available_emails = [u.email for u in all_users]
            user_count = len(available_emails)
            
            if not is_production:
                print(f"  No user found. Total users in DB: {user_count}")
                if user_count > 0:
                    print(f"  Available emails: {', '.join(available_emails[:10])}")
            
            # Always show debug info in non-production, or if we can't determine production status
            if not is_production or user_count == 0:
                if user_count == 0:
                    detail = f"Incorrect email or password. No users found in database. Searched for: '{searched_email}'. Please run: railway run python fix_dev_database.py"
                else:
                    detail = f"Incorrect email or password. Searched for: '{searched_email}'. Available emails ({user_count}): {', '.join(available_emails[:10])}"
                raise HTTPException(status_code=401, detail=detail)
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            # Error getting user list - still show helpful message
            print(f"  Error listing users: {e}")
            if not is_production:
                detail = f"Incorrect email or password. Searched for: '{searched_email}'. Error listing users: {str(e)}"
                raise HTTPException(status_code=401, detail=detail)
        
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )
    
    # NOTE: Password validation is disabled - any password is accepted
    # TODO: Add password verification when password fields are added
    # if not verify_password(credentials.password, user.hashed_password):
    #     raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Update last login
    from datetime import datetime
    try:
        user.last_login_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        # Log but don't fail login if update fails
        if not is_production:
            print(f"Warning: Failed to update last_login_at: {e}")
    
    # Create access token
    access_token_expires = timedelta(minutes=60 * 24 * 7)  # 7 days
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UserWithClients)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information with accessible clients."""
    # Get clients user has access to via memberships
    memberships = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.status == 'active'
    ).options(joinedload(Membership.client)).all()
    
    accessible_clients = [m.client for m in memberships if m.client]
    
    # If user is founder, also include clients they founded
    if current_user.is_founder:
        founded_clients = db.query(Client).filter(
            Client.founder_user_id == current_user.id
        ).all()
        # Merge and deduplicate
        client_ids = {c.id for c in accessible_clients}
        for client in founded_clients:
            if client.id not in client_ids:
                accessible_clients.append(client)
    
    return UserWithClients(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        is_founder=current_user.is_founder,
        is_active=current_user.is_active,
        email_verified_at=current_user.email_verified_at,
        created_at=current_user.created_at,
        accessible_clients=[ClientResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in accessible_clients]
    )


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

