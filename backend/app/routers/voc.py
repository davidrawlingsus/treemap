"""
VOC (Voice of Customer) data management routes.
"""
import csv
import hashlib
import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, func
from uuid import UUID
from typing import List, Optional
import logging

from app.database import get_db
from app.models import Client, Membership, ProcessVoc, User
from app.schemas import (
    ProcessVocResponse,
    DimensionQuestionInfo,
    VocSourceInfo,
    VocProjectInfo,
    VocClientInfo,
    CsvUploadResponse,
    CsvSaveResponse,
    CsvColumnMappingRequest,
)
from app.auth import get_current_user
from app.authorization import verify_client_access

router = APIRouter(prefix="/api/voc", tags=["voc"])
logger = logging.getLogger(__name__)


@router.get("/data", response_model=List[ProcessVocResponse])
def get_voc_data(
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get process_voc rows with optional filtering.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    - data_source: Filter by data source name (e.g., "email_survey")
    - project_name: Filter by project name
    - dimension_ref: Filter by dimension reference (e.g., "ref_ljwfv")
    """
    query = db.query(ProcessVoc)
    
    if client_uuid:
        # First, try to get client name from clients table
        client = db.query(Client).filter(Client.id == client_uuid).first()
        
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            # Fallback to just UUID if client not found
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    if data_source:
        query = query.filter(ProcessVoc.data_source == data_source)
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    if dimension_ref:
        query = query.filter(ProcessVoc.dimension_ref == dimension_ref)
    
    return query.all()


@router.get("/questions", response_model=List[DimensionQuestionInfo])
def get_voc_questions(
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List available dimensions/questions in process_voc.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    - data_source: Filter by data source name
    - project_name: Filter by project name
    """
    from sqlalchemy import func
    
    query = db.query(
        ProcessVoc.dimension_ref,
        ProcessVoc.dimension_name,
        func.count(ProcessVoc.id).label('response_count')
    )
    
    if client_uuid:
        # Get client name for matching
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    if data_source:
        query = query.filter(ProcessVoc.data_source == data_source)
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    
    query = query.group_by(
        ProcessVoc.dimension_ref,
        ProcessVoc.dimension_name
    )
    
    results = query.all()
    
    return [
        DimensionQuestionInfo(
            dimension_ref=row.dimension_ref,
            dimension_name=row.dimension_name,
            response_count=row.response_count
        )
        for row in results
    ]


@router.get("/sources", response_model=List[VocSourceInfo])
def get_voc_sources(
    client_uuid: Optional[UUID] = None,
    project_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List available data sources in process_voc.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    - project_name: Filter by project name
    """
    from sqlalchemy import func
    
    query = db.query(
        ProcessVoc.data_source,
        ProcessVoc.client_uuid,
        func.max(ProcessVoc.client_name).label('client_name'),
        func.count(ProcessVoc.id).label('response_count')
    )
    
    if client_uuid:
        # Get client name for matching
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    
    query = query.group_by(
        ProcessVoc.data_source,
        ProcessVoc.client_uuid
    )
    
    results = query.all()
    
    return [
        VocSourceInfo(
            data_source=row.data_source,
            client_uuid=row.client_uuid or client_uuid,  # Use provided UUID if row has null
            client_name=row.client_name,
            response_count=row.response_count
        )
        for row in results
        if row.data_source is not None
    ]


@router.get("/projects", response_model=List[VocProjectInfo])
def get_voc_projects(
    client_uuid: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    List available projects in process_voc for a client.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    """
    from sqlalchemy import func
    
    query = db.query(
        ProcessVoc.project_name,
        func.max(ProcessVoc.project_id).label('project_id'),
        func.count(ProcessVoc.id).label('response_count')
    )
    
    if client_uuid:
        # Get client name for matching
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    # Filter out null project names
    query = query.filter(ProcessVoc.project_name.isnot(None))
    
    query = query.group_by(
        ProcessVoc.project_name
    )
    
    results = query.all()
    
    return [
        VocProjectInfo(
            project_name=row.project_name,
            project_id=row.project_id,
            response_count=row.response_count
        )
        for row in results
        if row.project_name is not None
    ]


@router.get("/clients", response_model=List[VocClientInfo])
def get_voc_clients(
    db: Session = Depends(get_db)
):
    """
    List clients that have data in process_voc.
    Returns distinct clients with data source counts.
    Handles both cases: client_uuid set, or client_name only (tries to match to clients table).
    """
    from sqlalchemy import func, distinct, case
    
    # First, try to get clients grouped by client_uuid (when not null)
    query_with_uuid = db.query(
        ProcessVoc.client_uuid,
        func.max(ProcessVoc.client_name).label('client_name'),
        func.count(func.distinct(ProcessVoc.data_source)).label('data_source_count')
    ).filter(
        ProcessVoc.client_uuid.isnot(None)
    ).group_by(
        ProcessVoc.client_uuid
    )
    
    results_with_uuid = query_with_uuid.all()
    
    # Build a map of client_uuid -> info
    client_map = {}
    for row in results_with_uuid:
        client_map[row.client_uuid] = {
            'client_uuid': row.client_uuid,
            'client_name': row.client_name,
            'data_source_count': row.data_source_count
        }
    
    # Now get clients grouped by client_name (when client_uuid is null)
    # and try to match them to existing clients in the clients table
    query_by_name = db.query(
        ProcessVoc.client_name,
        func.count(func.distinct(ProcessVoc.data_source)).label('data_source_count')
    ).filter(
        ProcessVoc.client_uuid.is_(None),
        ProcessVoc.client_name.isnot(None)
    ).group_by(
        ProcessVoc.client_name
    )
    
    results_by_name = query_by_name.all()
    
    # For each client_name, try to find matching client in clients table
    for row in results_by_name:
        if row.client_name:
            # Try to find a client with matching name
            matching_client = db.query(Client).filter(Client.name == row.client_name).first()
            
            if matching_client:
                # Use the existing client UUID
                if matching_client.id not in client_map:
                    client_map[matching_client.id] = {
                        'client_uuid': matching_client.id,
                        'client_name': matching_client.name,
                        'data_source_count': row.data_source_count
                    }
                else:
                    # Merge data source counts if client already exists
                    client_map[matching_client.id]['data_source_count'] += row.data_source_count
            else:
                # No matching client found - we'll need to create a temporary UUID
                # For now, we'll skip these or create them on-the-fly
                # For the frontend, we can use client_name as identifier
                pass
    
    # Convert to list and return
    return [
        VocClientInfo(
            client_uuid=info['client_uuid'],
            client_name=info['client_name'],
            data_source_count=info['data_source_count']
        )
        for info in client_map.values()
    ]


@router.post("/upload-csv", response_model=CsvUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    project_name: str = Form(...),
    data_source: str = Form(...),
    client_uuid: UUID = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and parse a CSV file.
    
    Returns column headers, sample rows, row count, and full CSV data.
    Generates random IDs for project_id and data_source_id.
    """
    try:
        # Validate user has access to client
        verify_client_access(client_uuid, current_user, db)

        # Read and parse CSV
        contents = await file.read()
        
        # Try UTF-8 first, fallback to latin-1
        try:
            text_content = contents.decode('utf-8')
        except UnicodeDecodeError:
            text_content = contents.decode('latin-1')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(text_content))
        rows = list(csv_reader)
        
        if not rows:
            raise HTTPException(status_code=400, detail="CSV file is empty or has no data rows")
        
        # Get column headers
        column_headers = list(rows[0].keys())
        
        if not column_headers:
            raise HTTPException(status_code=400, detail="CSV file has no columns")
        
        # Count rows
        row_count = len(rows)
        
        # Generate random IDs
        project_id = str(uuid.uuid4())[:8]  # Short UUID
        data_source_id = str(uuid.uuid4())[:8]
        
        # Get sample rows (first 3)
        sample_rows = rows[:3]
        
        # Convert rows to list of dicts (ensure all values are strings)
        csv_data = []
        for row in rows:
            csv_data.append({k: str(v) if v is not None else '' for k, v in row.items()})
        
        return CsvUploadResponse(
            column_headers=column_headers,
            sample_rows=sample_rows,
            row_count=row_count,
            project_id=project_id,
            data_source_id=data_source_id,
            csv_data=csv_data,
            project_name=project_name,
            data_source=data_source
        )
        
    except csv.Error as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
    except Exception as e:
        logger.error(f"Error uploading CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


