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
    VocSummaryResponse,
    VocSummaryCategory,
    VocSummaryTopic,
)
from app.auth import get_current_user, get_current_user_flexible
from app.authorization import verify_client_access, get_user_clients

router = APIRouter(prefix="/api/voc", tags=["VOC Data"])
logger = logging.getLogger(__name__)


def _enforce_api_key_scope(current_user: User, client_uuid: Optional[UUID]) -> Optional[UUID]:
    """If authenticated via API key, enforce and default to the key's scoped client."""
    scoped_client_id = getattr(current_user, '_api_key_client_id', None)
    if scoped_client_id is None:
        return client_uuid  # JWT auth, no override
    if client_uuid and client_uuid != scoped_client_id:
        raise HTTPException(status_code=403, detail="API key is scoped to a different client")
    return scoped_client_id


@router.get("/data", response_model=List[ProcessVocResponse], summary="Get raw verbatim rows")
def get_voc_data(
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Fetch raw VOC verbatim rows with optional filtering.

    When using an API key, results are automatically scoped to the key's client.
    All filter parameters are optional and combinable.

    - **client_uuid**: Filter by client UUID (auto-set when using API key)
    - **data_source**: Filter by data source name (e.g. `trustpilot`, `email_survey`)
    - **project_name**: Filter by project name
    - **dimension_ref**: Filter by dimension/question reference (e.g. `ref_ljwfv`)
    """
    client_uuid = _enforce_api_key_scope(current_user, client_uuid)
    query = db.query(ProcessVoc)

    if client_uuid:
        verify_client_access(client_uuid, current_user, db)
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
    else:
        # No client_uuid provided: restrict to user's accessible clients
        accessible = get_user_clients(current_user, db)
        accessible_ids = [c.id for c in accessible]
        accessible_names = [c.name for c in accessible]
        query = query.filter(
            or_(
                ProcessVoc.client_uuid.in_(accessible_ids),
                ProcessVoc.client_name.in_(accessible_names),
            )
        )

    if data_source:
        query = query.filter(ProcessVoc.data_source == data_source)
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    if dimension_ref:
        query = query.filter(ProcessVoc.dimension_ref == dimension_ref)
    
    return query.all()


from app.services.voc_summary_service import build_voc_summary_dict


@router.get("/summary", response_model=VocSummaryResponse, summary="Get structured VOC summary")
def get_voc_summary(
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Get a hierarchical summary of VOC data: **Category → Topic → sample verbatims**.

    Returns aggregated counts and representative verbatims for each topic,
    organised by category. Ideal for understanding themes at a glance.

    - **client_uuid**: Filter by client UUID (auto-set when using API key)
    - **data_source**: Filter by data source name
    - **project_name**: Filter by project name
    - **dimension_ref**: Filter by dimension/question reference
    """
    client_uuid = _enforce_api_key_scope(current_user, client_uuid)
    if client_uuid:
        verify_client_access(client_uuid, current_user, db)
    summary = build_voc_summary_dict(
        db, client_uuid=client_uuid, data_source=data_source,
        project_name=project_name, dimension_ref=dimension_ref
    )
    categories = [
        VocSummaryCategory(
            name=c["name"],
            topics=[VocSummaryTopic(**t) for t in c["topics"]]
        )
        for c in summary["categories"]
    ]
    return VocSummaryResponse(
        categories=categories,
        total_verbatims=summary["total_verbatims"]
    )


@router.get("/questions", response_model=List[DimensionQuestionInfo], summary="List dimensions/questions")
def get_voc_questions(
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    List available dimensions (survey questions) with response counts.

    Use this to discover which questions/dimensions exist before fetching data.
    Returns `dimension_ref` values you can pass to `/data` or `/summary`.

    - **client_uuid**: Filter by client UUID (auto-set when using API key)
    - **data_source**: Filter by data source name
    - **project_name**: Filter by project name
    """
    from sqlalchemy import func

    client_uuid = _enforce_api_key_scope(current_user, client_uuid)
    if client_uuid:
        verify_client_access(client_uuid, current_user, db)

    query = db.query(
        ProcessVoc.dimension_ref,
        ProcessVoc.dimension_name,
        func.count(ProcessVoc.id).label('response_count'),
        func.max(ProcessVoc.question_type).label('question_type')
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
            response_count=row.response_count,
            question_type=row.question_type
        )
        for row in results
    ]


@router.get("/sources", response_model=List[VocSourceInfo], summary="List data sources")
def get_voc_sources(
    client_uuid: Optional[UUID] = None,
    project_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    List available data sources (e.g. `trustpilot`, `email_survey`, `google_reviews`)
    with response counts.

    Use this to discover which sources exist before filtering `/data` or `/summary`.

    - **client_uuid**: Filter by client UUID (auto-set when using API key)
    - **project_name**: Filter by project name
    """
    from sqlalchemy import func

    client_uuid = _enforce_api_key_scope(current_user, client_uuid)
    if client_uuid:
        verify_client_access(client_uuid, current_user, db)

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


@router.get("/projects", response_model=List[VocProjectInfo], summary="List projects")
def get_voc_projects(
    client_uuid: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    List projects that contain VOC data, with response counts.

    - **client_uuid**: Filter by client UUID (auto-set when using API key)
    """
    from sqlalchemy import func

    client_uuid = _enforce_api_key_scope(current_user, client_uuid)
    if client_uuid:
        verify_client_access(client_uuid, current_user, db)

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


@router.get("/clients", response_model=List[VocClientInfo], summary="List accessible clients")
def get_voc_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    List clients that have VOC data and are accessible to the current user.

    When using an API key, returns only the key's scoped client.
    When using JWT, returns all clients the user has access to.

    Each client includes a `data_source_count` showing how many distinct data sources are available.
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
        # Fetch logo_url and header_color from clients table
        client = db.query(Client).filter(Client.id == row.client_uuid).first()
        client_map[row.client_uuid] = {
            'client_uuid': row.client_uuid,
            'client_name': row.client_name,
            'data_source_count': row.data_source_count,
            'logo_url': client.logo_url if client else None,
            'header_color': client.header_color if client else None,
            'is_lead': client.is_lead if client else False
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
                        'data_source_count': row.data_source_count,
                        'logo_url': matching_client.logo_url,
                        'header_color': matching_client.header_color,
                        'is_lead': matching_client.is_lead
                    }
                else:
                    # Merge data source counts if client already exists
                    client_map[matching_client.id]['data_source_count'] += row.data_source_count
            else:
                # No matching client found - we'll need to create a temporary UUID
                # For now, we'll skip these or create them on-the-fly
                # For the frontend, we can use client_name as identifier
                pass
    
    # Filter to only clients the user can access
    scoped_client_id = getattr(current_user, '_api_key_client_id', None)
    if scoped_client_id:
        accessible_ids = {scoped_client_id}
    else:
        accessible = get_user_clients(current_user, db)
        accessible_ids = {c.id for c in accessible}

    # Convert to list and return
    return [
        VocClientInfo(
            client_uuid=info['client_uuid'],
            client_name=info['client_name'],
            data_source_count=info['data_source_count'],
            logo_url=info.get('logo_url'),
            header_color=info.get('header_color'),
            is_lead=info.get('is_lead', False)
        )
        for info in client_map.values()
        if info['client_uuid'] in accessible_ids
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


