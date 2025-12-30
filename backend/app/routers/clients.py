"""
Client and insight management routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from uuid import UUID
from typing import List, Optional
import logging

from app.database import get_db
from app.models import Client, DataSource, Insight, Membership, User
from app.schemas import (
    ClientCreate,
    ClientResponse,
    DataSourceResponse,
    InsightCreate,
    InsightUpdate,
    InsightResponse,
    InsightListResponse,
    InsightOrigin,
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/clients", tags=["clients"])
logger = logging.getLogger(__name__)


def verify_client_access(client_id: UUID, current_user: User, db: Session) -> Client:
    """Verify that the current user has access to the specified client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if user has access via memberships
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.client_id == client_id,
        Membership.status == 'active'
    ).first()
    
    if membership:
        return client
    
    # If user is founder, check if they founded this client
    if current_user.is_founder and client.founder_user_id == current_user.id:
        return client
    
    raise HTTPException(
        status_code=403,
        detail="You do not have access to this client"
    )


@router.get("", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    """List all clients"""
    clients = db.query(Client).order_by(Client.name).all()
    return clients


@router.post("", response_model=ClientResponse)
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


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: UUID, db: Session = Depends(get_db)):
    """Get a specific client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return client


@router.get("/{client_id}/sources", response_model=List[DataSourceResponse])
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


@router.get("/{client_id}/insights", response_model=InsightListResponse)
def list_insights(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    origin_type: Optional[str] = None,
    type: Optional[str] = None,
    project_name: Optional[str] = None,
    data_source: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    category: Optional[str] = None,
    topic_label: Optional[str] = None,
    process_voc_id: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
):
    """List insights for a client with filtering and sorting"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    # Build base query
    query = db.query(Insight).filter(Insight.client_id == client_id)
    
    # Apply filters using JSONB operators
    # For array filtering, we check if any element in the origins array matches
    if origin_type:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'origin_type') = '{origin_type}')")
        )
    
    if type:
        query = query.filter(Insight.type == type)
    
    if project_name:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'project_name') = '{project_name}')")
        )
    
    if data_source:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'data_source') = '{data_source}')")
        )
    
    if dimension_ref:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'dimension_ref') = '{dimension_ref}')")
        )
    
    if category:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'category') = '{category}')")
        )
    
    if topic_label:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'topic_label') = '{topic_label}')")
        )
    
    if process_voc_id is not None:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'process_voc_id')::int = {process_voc_id})")
        )
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_order.lower() == "asc":
        if sort_by == "name":
            query = query.order_by(Insight.name.asc())
        elif sort_by == "type":
            query = query.order_by(Insight.type.asc())
        elif sort_by == "created_at":
            query = query.order_by(Insight.created_at.asc())
        elif sort_by == "updated_at":
            query = query.order_by(Insight.updated_at.asc())
        else:
            query = query.order_by(Insight.created_at.asc())
    else:
        if sort_by == "name":
            query = query.order_by(Insight.name.desc())
        elif sort_by == "type":
            query = query.order_by(Insight.type.desc())
        elif sort_by == "created_at":
            query = query.order_by(Insight.created_at.desc())
        elif sort_by == "updated_at":
            query = query.order_by(Insight.updated_at.desc())
        else:
            query = query.order_by(Insight.created_at.desc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    insights = query.offset(offset).limit(page_size).all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return InsightListResponse(
        items=[InsightResponse.from_orm(insight) for insight in insights],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/{client_id}/insights", response_model=InsightResponse)
def create_insight(
    client_id: UUID,
    insight_data: InsightCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new insight"""
    try:
        # Verify client access
        verify_client_access(client_id, current_user, db)
        
        # Convert origins to JSONB format
        origins_json = [origin.model_dump() for origin in insight_data.origins]
        
        insight = Insight(
            client_id=client_id,
            name=insight_data.name,
            type=insight_data.type,
            application=insight_data.application,
            description=insight_data.description,
            notes=insight_data.notes,
            status=insight_data.status or 'Not Started',
            origins=origins_json,
            verbatims=insight_data.verbatims or [],
            meta_data=insight_data.metadata or {},
            created_by=current_user.id,
        )
        
        db.add(insight)
        db.commit()
        db.refresh(insight)
        
        return InsightResponse.from_orm(insight)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating insight: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create insight: {str(e)}")


@router.get("/{client_id}/insights/{insight_id}", response_model=InsightResponse)
def get_insight(
    client_id: UUID,
    insight_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    return InsightResponse.from_orm(insight)


@router.put("/{client_id}/insights/{insight_id}", response_model=InsightResponse)
def update_insight(
    client_id: UUID,
    insight_id: UUID,
    insight_data: InsightUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Update fields
    if insight_data.name is not None:
        insight.name = insight_data.name
    if insight_data.type is not None:
        insight.type = insight_data.type
    if insight_data.application is not None:
        insight.application = insight_data.application
    if insight_data.description is not None:
        insight.description = insight_data.description
    if insight_data.notes is not None:
        logger.info(f"Updating notes for insight {insight_id}, length: {len(insight_data.notes)}")
        logger.info(f"Notes content (first 500 chars): {insight_data.notes[:500]}")
        logger.info(f"Notes content (last 100 chars): {insight_data.notes[-100:]}")
        # Check if notes contains img tag
        if '<img' in insight_data.notes:
            import re
            img_matches = re.findall(r'<img[^>]+src="([^"]+)"', insight_data.notes)
            logger.info(f"Found {len(img_matches)} image(s) in notes")
            for i, img_src in enumerate(img_matches):
                logger.info(f"Image {i+1} src: {img_src}")
                logger.info(f"Image {i+1} src length: {len(img_src)}")
                if not img_src.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    logger.warning(f"Image {i+1} src does not end with image extension - may be truncated!")
        insight.notes = insight_data.notes
    if insight_data.status is not None:
        insight.status = insight_data.status
    if insight_data.verbatims is not None:
        insight.verbatims = insight_data.verbatims
    if insight_data.metadata is not None:
        insight.meta_data = insight_data.metadata
    
    # Handle origins - if add_origin is provided, append; if origins is provided, replace
    if insight_data.add_origin is not None:
        current_origins = insight.origins if insight.origins else []
        current_origins.append(insight_data.add_origin.model_dump())
        insight.origins = current_origins
    elif insight_data.origins is not None:
        insight.origins = [origin.model_dump() for origin in insight_data.origins]
    
    db.commit()
    db.refresh(insight)
    
    return InsightResponse.from_orm(insight)


@router.delete("/{client_id}/insights/{insight_id}")
def delete_insight(
    client_id: UUID,
    insight_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    db.delete(insight)
    db.commit()
    
    return {"message": "Insight deleted successfully"}


@router.post("/{client_id}/insights/{insight_id}/origins", response_model=InsightResponse)
def add_insight_origin(
    client_id: UUID,
    insight_id: UUID,
    origin: InsightOrigin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new origin to an existing insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Append new origin
    current_origins = insight.origins if insight.origins else []
    current_origins.append(origin.model_dump())
    insight.origins = current_origins
    
    db.commit()
    db.refresh(insight)
    
    return InsightResponse.from_orm(insight)

