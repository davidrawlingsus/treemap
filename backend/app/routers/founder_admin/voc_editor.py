"""
VOC (Voice of Customer) data editing routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User, ProcessVoc
from app.schemas import (
    ProcessVocAdminListResponse,
    ProcessVocBulkUpdateRequest,
    ProcessVocBulkUpdateResponse,
    FieldMetadataResponse,
    FieldMetadata,
    DynamicBulkUpdateRequest,
)
from app.auth import get_current_active_founder_with_password

router = APIRouter()


@router.get("/api/founder-admin/voc-data", response_model=ProcessVocAdminListResponse)
def get_founder_admin_voc_data(
    filter_project_id: Optional[str] = None,
    filter_project_name: Optional[str] = None,
    filter_dimension_ref: Optional[str] = None,
    filter_dimension_name: Optional[str] = None,
    filter_client_name: Optional[str] = None,
    filter_data_source: Optional[str] = None,
    # Legacy parameter names for backward compatibility
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    client_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password)
):
    """
    Get all process_voc rows with optional filtering.
    Requires founder authentication.
    Returns paginated results.
    
    Supports both filter_* parameter names and legacy names.
    """
    # Build query
    query = db.query(ProcessVoc)
    
    # Support both new and legacy parameter names
    filter_pid = filter_project_id or project_id
    filter_pname = filter_project_name or project_name
    filter_dref = filter_dimension_ref or dimension_ref
    filter_dname = filter_dimension_name
    filter_cname = filter_client_name or client_name
    
    # Apply filters (case-insensitive partial matching)
    if filter_pid:
        query = query.filter(ProcessVoc.project_id.ilike(f"%{filter_pid}%"))
    if filter_pname:
        query = query.filter(ProcessVoc.project_name.ilike(f"%{filter_pname}%"))
    if filter_dref:
        query = query.filter(ProcessVoc.dimension_ref.ilike(f"%{filter_dref}%"))
    if filter_dname:
        query = query.filter(ProcessVoc.dimension_name.ilike(f"%{filter_dname}%"))
    if filter_cname:
        query = query.filter(ProcessVoc.client_name.ilike(f"%{filter_cname}%"))
    if filter_data_source:
        query = query.filter(ProcessVoc.data_source.ilike(f"%{filter_data_source}%"))
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    
    # Get paginated results
    items = query.order_by(ProcessVoc.id).offset(offset).limit(page_size).all()
    
    return ProcessVocAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/api/founder-admin/voc-data/bulk-update", response_model=ProcessVocBulkUpdateResponse)
def bulk_update_voc_data(
    update_request: ProcessVocBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password)
):
    """
    Bulk update project_name and/or dimension_name for multiple process_voc rows.
    Requires founder authentication.
    """
    updated_count = 0
    
    for update_item in update_request.updates:
        # Find the row by ID
        row = db.query(ProcessVoc).filter(ProcessVoc.id == update_item.id).first()
        
        if not row:
            continue  # Skip if row not found
        
        # Update fields if provided
        if update_item.project_name is not None:
            row.project_name = update_item.project_name
        if update_item.dimension_name is not None:
            row.dimension_name = update_item.dimension_name
        if update_item.data_source is not None:
            row.data_source = update_item.data_source
        if update_item.client_name is not None:
            row.client_name = update_item.client_name
        if hasattr(update_item, 'question_text') and update_item.question_text is not None:
            row.question_text = update_item.question_text
        
        updated_count += 1
    
    # Commit all changes
    db.commit()
    
    return ProcessVocBulkUpdateResponse(
        updated_count=updated_count,
        message=f"Successfully updated {updated_count} row(s)"
    )


@router.get("/api/founder-admin/field-metadata", response_model=FieldMetadataResponse)
def get_field_metadata(
    current_user: User = Depends(get_current_active_founder_with_password)
):
    """
    Get metadata about all editable fields in process_voc table.
    Requires founder authentication.
    """
    fields = [
        # Client fields
        FieldMetadata(name="client_name", type="string", nullable=True, category="client", editable=True),
        FieldMetadata(name="client_id", type="string", nullable=True, category="client", editable=True),
        # Project fields
        FieldMetadata(name="project_name", type="string", nullable=True, category="project", editable=True),
        FieldMetadata(name="project_id", type="string", nullable=True, category="project", editable=True),
        # Dimension fields
        FieldMetadata(name="dimension_name", type="text", nullable=True, category="dimension", editable=True),
        FieldMetadata(name="dimension_ref", type="string", nullable=False, category="dimension", editable=True),
        # Response fields
        FieldMetadata(name="data_source", type="string", nullable=True, category="response", editable=True),
        FieldMetadata(name="value", type="text", nullable=True, category="response", editable=True),
        FieldMetadata(name="overall_sentiment", type="string", nullable=True, category="response", editable=True),
        FieldMetadata(name="response_type", type="string", nullable=True, category="response", editable=True),
        FieldMetadata(name="user_type", type="string", nullable=True, category="response", editable=True),
        FieldMetadata(name="question_text", type="text", nullable=True, category="response", editable=True),
        # Metadata fields
        FieldMetadata(name="region", type="string", nullable=True, category="metadata", editable=True),
        FieldMetadata(name="total_rows", type="integer", nullable=True, category="metadata", editable=True),
        FieldMetadata(name="respondent_id", type="string", nullable=False, category="metadata", editable=True),
        # Timestamp fields
        FieldMetadata(name="created", type="datetime", nullable=True, category="timestamp", editable=True),
        FieldMetadata(name="last_modified", type="datetime", nullable=True, category="timestamp", editable=True),
        FieldMetadata(name="start_date", type="datetime", nullable=True, category="timestamp", editable=True),
        FieldMetadata(name="submit_date", type="datetime", nullable=True, category="timestamp", editable=True),
        # Complex fields
        FieldMetadata(name="topics", type="json", nullable=True, category="response", editable=True),
    ]
    
    return FieldMetadataResponse(fields=fields)


@router.post("/api/founder-admin/voc-data/bulk-update-filtered", response_model=ProcessVocBulkUpdateResponse)
def bulk_update_filtered_voc_data(
    filter_project_id: Optional[str] = None,
    filter_project_name: Optional[str] = None,
    filter_dimension_ref: Optional[str] = None,
    filter_dimension_name: Optional[str] = None,
    filter_client_name: Optional[str] = None,
    filter_data_source: Optional[str] = None,
    update_request: Optional[DynamicBulkUpdateRequest] = None,
    # Legacy parameters for backward compatibility
    project_name: Optional[str] = None,
    dimension_name: Optional[str] = None,
    data_source: Optional[str] = None,
    client_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password)
):
    """
    Bulk update any fields for all rows matching filter criteria.
    Requires founder authentication.
    At least one filter must be provided.
    
    Supports two modes:
    1. Legacy: Use individual parameters (project_name, dimension_name, etc.)
    2. New: Use update_request with dynamic field map
    """
    # Require at least one filter to prevent accidental updates to all rows
    if not filter_project_id and not filter_project_name and not filter_dimension_ref and not filter_dimension_name and not filter_client_name and not filter_data_source:
        raise HTTPException(
            status_code=400,
            detail="At least one filter must be provided"
        )
    
    # Build update map - support both legacy and new format
    updates = {}
    if update_request:
        updates = update_request.updates
    else:
        # Legacy mode
        if project_name is not None:
            updates["project_name"] = project_name
        if dimension_name is not None:
            updates["dimension_name"] = dimension_name
        if data_source is not None:
            updates["data_source"] = data_source
        if client_name is not None:
            updates["client_name"] = client_name
    
    # Remove None values (fields to skip)
    updates = {k: v for k, v in updates.items() if v is not None}
    
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="At least one field to update must be provided"
        )
    
    # Build query with filters (case-insensitive partial matching)
    query = db.query(ProcessVoc)
    
    if filter_project_id:
        query = query.filter(ProcessVoc.project_id.ilike(f"%{filter_project_id}%"))
    if filter_project_name:
        query = query.filter(ProcessVoc.project_name.ilike(f"%{filter_project_name}%"))
    if filter_dimension_ref:
        query = query.filter(ProcessVoc.dimension_ref.ilike(f"%{filter_dimension_ref}%"))
    if filter_dimension_name:
        query = query.filter(ProcessVoc.dimension_name.ilike(f"%{filter_dimension_name}%"))
    if filter_client_name:
        query = query.filter(ProcessVoc.client_name.ilike(f"%{filter_client_name}%"))
    if filter_data_source:
        query = query.filter(ProcessVoc.data_source.ilike(f"%{filter_data_source}%"))
    
    # Get all matching rows
    rows = query.all()
    updated_count = 0
    
    # Define which fields are editable (exclude auto fields and relationships)
    editable_fields = {
        'client_name', 'client_id', 'project_name', 'project_id',
        'dimension_name', 'dimension_ref', 'data_source', 'value',
        'overall_sentiment', 'response_type', 'user_type', 'region',
        'total_rows', 'respondent_id', 'created', 'last_modified',
        'start_date', 'submit_date', 'topics', 'question_text'
    }
    
    for row in rows:
        updated = False
        for field_name, new_value in updates.items():
            if field_name not in editable_fields:
                continue  # Skip non-editable fields
            
            if hasattr(row, field_name):
                # Handle different field types
                if field_name == 'topics' and new_value:
                    # Parse JSON for topics
                    try:
                        import json
                        row.topics = json.loads(new_value) if isinstance(new_value, str) else new_value
                    except:
                        continue  # Skip invalid JSON
                elif field_name == 'total_rows' and new_value:
                    # Parse integer
                    try:
                        row.total_rows = int(new_value)
                    except:
                        continue
                elif field_name in ['created', 'last_modified', 'start_date', 'submit_date'] and new_value:
                    # Parse datetime
                    try:
                        from datetime import datetime
                        row.__setattr__(field_name, datetime.fromisoformat(new_value.replace('Z', '+00:00')))
                    except:
                        continue
                else:
                    # String/text fields
                    row.__setattr__(field_name, new_value)
                updated = True
        
        if updated:
            updated_count += 1
    
    # Commit all changes
    db.commit()
    
    return ProcessVocBulkUpdateResponse(
        updated_count=updated_count,
        message=f"Successfully updated {updated_count} row(s) matching filters"
    )


@router.delete("/api/founder-admin/voc-data/bulk-delete", response_model=ProcessVocBulkUpdateResponse)
def bulk_delete_voc_data(
    filter_project_id: Optional[str] = None,
    filter_project_name: Optional[str] = None,
    filter_dimension_ref: Optional[str] = None,
    filter_dimension_name: Optional[str] = None,
    filter_client_name: Optional[str] = None,
    filter_data_source: Optional[str] = None,
    # Legacy parameters
    project_id: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password)
):
    """
    Bulk delete all rows matching filter criteria.
    Requires founder authentication.
    At least one filter must be provided.
    """
    # Support both new and legacy parameter names
    filter_pid = filter_project_id or project_id
    filter_pname = filter_project_name
    filter_dref = filter_dimension_ref or dimension_ref
    filter_dname = filter_dimension_name
    filter_cname = filter_client_name
    
    # Require at least one filter to prevent accidental deletion of all rows
    if not filter_pid and not filter_pname and not filter_dref and not filter_dname and not filter_cname and not filter_data_source:
        raise HTTPException(
            status_code=400,
            detail="At least one filter must be provided"
        )
    
    # Build query with filters (case-insensitive partial matching)
    query = db.query(ProcessVoc)
    
    if filter_pid:
        query = query.filter(ProcessVoc.project_id.ilike(f"%{filter_pid}%"))
    if filter_pname:
        query = query.filter(ProcessVoc.project_name.ilike(f"%{filter_pname}%"))
    if filter_dref:
        query = query.filter(ProcessVoc.dimension_ref.ilike(f"%{filter_dref}%"))
    if filter_dname:
        query = query.filter(ProcessVoc.dimension_name.ilike(f"%{filter_dname}%"))
    if filter_cname:
        query = query.filter(ProcessVoc.client_name.ilike(f"%{filter_cname}%"))
    if filter_data_source:
        query = query.filter(ProcessVoc.data_source.ilike(f"%{filter_data_source}%"))
    
    # Get all matching rows
    rows = query.all()
    deleted_count = len(rows)
    
    # Delete all matching rows
    for row in rows:
        db.delete(row)
    
    # Commit all changes
    db.commit()
    
    return ProcessVocBulkUpdateResponse(
        updated_count=deleted_count,
        message=f"Successfully deleted {deleted_count} row(s) matching filters"
    )

