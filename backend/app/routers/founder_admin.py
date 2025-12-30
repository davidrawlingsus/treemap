"""
Founder admin routes for user management, authorized domains, VOC data admin, and database management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, or_, func, inspect, MetaData, Table, Column as SAColumn, Integer, String, DateTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import sqltypes
from uuid import UUID
from typing import List, Optional
import logging

from app.database import get_db, engine
from app.models import User, Membership, Client, AuthorizedDomain, AuthorizedDomainClient, ProcessVoc
from app.schemas import (
    FounderUserSummary,
    FounderUserMembership,
    ClientResponse,
    AuthorizedDomainResponse,
    AuthorizedDomainCreate,
    AuthorizedDomainUpdate,
    ProcessVocAdminListResponse,
    ProcessVocBulkUpdateRequest,
    ProcessVocBulkUpdateResponse,
    FieldMetadataResponse,
    FieldMetadata,
    DynamicBulkUpdateRequest,
    TableInfo,
    ColumnInfo,
    TableDataResponse,
    RowCreateRequest,
    RowUpdateRequest,
    TableCreateRequest,
    ColumnAddRequest,
)
from app.auth import get_current_active_founder
from app.utils import serialize_authorized_domain

router = APIRouter(tags=["founder-admin"])
logger = logging.getLogger(__name__)


def build_founder_user_summary(user: User) -> FounderUserSummary:
    """Build a founder-oriented view of a user record."""
    email_domain = user.email.split("@")[-1].lower() if "@" in user.email else ""
    membership_summaries: List[FounderUserMembership] = []
    for membership in user.memberships:
        if membership.client is None:
            continue
        membership_summaries.append(
            FounderUserMembership(
                client=ClientResponse.model_validate(membership.client),
                role=membership.role,
                status=membership.status,
                provisioned_at=membership.provisioned_at,
                provisioning_method=membership.provisioning_method,
                joined_at=membership.joined_at,
            )
        )

    return FounderUserSummary(
        id=user.id,
        email=user.email,
        name=user.name,
        is_founder=user.is_founder,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        email_verified_at=user.email_verified_at,
        last_magic_link_sent_at=user.last_magic_link_sent_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        email_domain=email_domain,
        memberships=membership_summaries,
    )


@router.get("/api/founder/users", response_model=List[FounderUserSummary])
def list_founder_users(
    search: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List users with membership metadata for founder tooling."""
    query = db.query(User)

    if client_id:
        query = query.join(Membership, Membership.user_id == User.id).filter(
            Membership.client_id == client_id
        )

    if search:
        normalized = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(User.email).like(normalized),
                func.lower(User.name).like(normalized),
            )
        )

    if domain:
        normalized_domain = domain.lower()
        query = query.filter(
            func.lower(User.email).like(f"%@{normalized_domain}")
        )

    users = (
        query.options(
            joinedload(User.memberships).joinedload(Membership.client)
        )
        .order_by(func.lower(User.email))
        .all()
    )

    # Deduplicate in case joins introduced duplicates
    unique_users = {user.id: user for user in users}.values()

    return [build_founder_user_summary(user) for user in unique_users]


@router.get(
    "/api/founder/authorized-domains",
    response_model=List[AuthorizedDomainResponse],
)
def list_authorized_domains_for_founder(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List authorized domains with associated clients for founder tooling."""
    domains = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .order_by(func.lower(AuthorizedDomain.domain))
        .all()
    )

    return [serialize_authorized_domain(domain) for domain in domains]


@router.post(
    "/api/founder/authorized-domains",
    response_model=AuthorizedDomainResponse,
    status_code=201,
)
def create_authorized_domain_for_founder(
    payload: AuthorizedDomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new authorized domain and associate it with clients."""
    normalized_domain = payload.domain.strip().lower()
    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required.")

    existing = (
        db.query(AuthorizedDomain)
        .filter(func.lower(AuthorizedDomain.domain) == normalized_domain)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )

    client_ids = set(payload.client_ids or [])
    clients: List[Client] = []
    if client_ids:
        clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
        found_ids = {client.id for client in clients}
        missing = client_ids - found_ids
        if missing:
            raise HTTPException(
                status_code=404,
                detail="One or more selected clients were not found.",
            )

    authorized_domain = AuthorizedDomain(
        domain=normalized_domain,
        description=payload.description.strip() if payload.description else None,
    )
    authorized_domain.clients = clients

    try:
        db.add(authorized_domain)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    created_domain = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .filter(AuthorizedDomain.id == authorized_domain.id)
        .one()
    )

    return serialize_authorized_domain(created_domain)


@router.put(
    "/api/founder/authorized-domains/{domain_id}",
    response_model=AuthorizedDomainResponse,
)
def update_authorized_domain_for_founder(
    domain_id: UUID,
    payload: AuthorizedDomainUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update an existing authorized domain and its client associations."""
    authorized_domain = (
        db.query(AuthorizedDomain)
        .options(joinedload(AuthorizedDomain.client_links))
        .filter(AuthorizedDomain.id == domain_id)
        .first()
    )

    if not authorized_domain:
        raise HTTPException(status_code=404, detail="Authorized domain not found.")

    normalized_domain = payload.domain.strip().lower()
    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required.")

    if normalized_domain != authorized_domain.domain:
        duplicate = (
            db.query(AuthorizedDomain)
            .filter(func.lower(AuthorizedDomain.domain) == normalized_domain)
            .filter(AuthorizedDomain.id != domain_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail="Another authorized domain with this name already exists.",
            )
        authorized_domain.domain = normalized_domain

    authorized_domain.description = (
        payload.description.strip() if payload.description else None
    )

    if payload.client_ids is not None:
        client_ids = set(payload.client_ids)
        clients: List[Client] = []
        if client_ids:
            clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
            found_ids = {client.id for client in clients}
            missing = client_ids - found_ids
            if missing:
                raise HTTPException(
                    status_code=404,
                    detail="One or more selected clients were not found.",
                )
        authorized_domain.clients = clients

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    updated_domain = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .filter(AuthorizedDomain.id == domain_id)
        .one()
    )

    return serialize_authorized_domain(updated_domain)




# Founder Admin Endpoints

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
    current_user: User = Depends(get_current_active_founder)
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
    current_user: User = Depends(get_current_active_founder)
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
    current_user: User = Depends(get_current_active_founder)
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
    current_user: User = Depends(get_current_active_founder)
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
    current_user: User = Depends(get_current_active_founder)
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


# AI Dimension Summary Endpoints


@router.get("/api/founder/database/tables", response_model=List[TableInfo])
def list_database_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all tables in the database with their column information."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    result = []
    for table_name in tables:
        # Skip alembic version table
        if table_name == 'alembic_version':
            continue
            
        columns = inspector.get_columns(table_name)
        column_info = []
        
        for col in columns:
            # Get primary key info
            pk_constraint = inspector.get_pk_constraint(table_name)
            is_pk = col['name'] in (pk_constraint.get('constrained_columns', []) or [])
            
            # Get foreign key info
            fk_info = None
            foreign_keys = inspector.get_foreign_keys(table_name)
            for fk in foreign_keys:
                if col['name'] in fk.get('constrained_columns', []):
                    fk_info = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                    break
            
            # Convert SQLAlchemy type to string
            col_type = str(col['type'])
            # Simplify type names
            if 'VARCHAR' in col_type or 'TEXT' in col_type or 'CHAR' in col_type:
                col_type = 'string'
            elif 'INTEGER' in col_type or 'BIGINT' in col_type or 'SMALLINT' in col_type:
                col_type = 'integer'
            elif 'BOOLEAN' in col_type:
                col_type = 'boolean'
            elif 'TIMESTAMP' in col_type or 'DATETIME' in col_type:
                col_type = 'datetime'
            elif 'UUID' in col_type:
                col_type = 'uuid'
            elif 'JSON' in col_type or 'JSONB' in col_type:
                col_type = 'json'
            elif 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type or 'REAL' in col_type:
                col_type = 'numeric'
            
            column_info.append(ColumnInfo(
                name=col['name'],
                type=col_type,
                nullable=col.get('nullable', True),
                primary_key=is_pk,
                foreign_key=fk_info,
                default=str(col.get('default', '')) if col.get('default') is not None else None
            ))
        
        # Get row count
        try:
            row_count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = row_count_result.scalar()
        except Exception:
            row_count = None
        
        result.append(TableInfo(
            name=table_name,
            row_count=row_count,
            columns=column_info
        ))
    
    # Sort by table name
    result.sort(key=lambda x: x.name)
    return result


@router.get("/api/founder/database/tables/{table_name}/columns", response_model=List[ColumnInfo])
def get_table_columns(
    table_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get column information for a specific table."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    columns = inspector.get_columns(table_name)
    pk_constraint = inspector.get_pk_constraint(table_name)
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    result = []
    for col in columns:
        is_pk = col['name'] in (pk_constraint.get('constrained_columns', []) or [])
        
        fk_info = None
        for fk in foreign_keys:
            if col['name'] in fk.get('constrained_columns', []):
                fk_info = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                break
        
        col_type = str(col['type'])
        if 'VARCHAR' in col_type or 'TEXT' in col_type or 'CHAR' in col_type:
            col_type = 'string'
        elif 'INTEGER' in col_type or 'BIGINT' in col_type or 'SMALLINT' in col_type:
            col_type = 'integer'
        elif 'BOOLEAN' in col_type:
            col_type = 'boolean'
        elif 'TIMESTAMP' in col_type or 'DATETIME' in col_type:
            col_type = 'datetime'
        elif 'UUID' in col_type:
            col_type = 'uuid'
        elif 'JSON' in col_type or 'JSONB' in col_type:
            col_type = 'json'
        elif 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type or 'REAL' in col_type:
            col_type = 'numeric'
        
        result.append(ColumnInfo(
            name=col['name'],
            type=col_type,
            nullable=col.get('nullable', True),
            primary_key=is_pk,
            foreign_key=fk_info,
            default=str(col.get('default', '')) if col.get('default') is not None else None
        ))
    
    return result


@router.get("/api/founder/database/tables/{table_name}/data", response_model=TableDataResponse)
def get_table_data(
    table_name: str,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get paginated data from a specific table."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get column info
    columns = inspector.get_columns(table_name)
    pk_constraint = inspector.get_pk_constraint(table_name)
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    column_info = []
    pk_columns = pk_constraint.get('constrained_columns', []) or []
    
    for col in columns:
        is_pk = col['name'] in pk_columns
        
        fk_info = None
        for fk in foreign_keys:
            if col['name'] in fk.get('constrained_columns', []):
                fk_info = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                break
        
        col_type = str(col['type'])
        if 'VARCHAR' in col_type or 'TEXT' in col_type or 'CHAR' in col_type:
            col_type = 'string'
        elif 'INTEGER' in col_type or 'BIGINT' in col_type or 'SMALLINT' in col_type:
            col_type = 'integer'
        elif 'BOOLEAN' in col_type:
            col_type = 'boolean'
        elif 'TIMESTAMP' in col_type or 'DATETIME' in col_type:
            col_type = 'datetime'
        elif 'UUID' in col_type:
            col_type = 'uuid'
        elif 'JSON' in col_type or 'JSONB' in col_type:
            col_type = 'json'
        elif 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type or 'REAL' in col_type:
            col_type = 'numeric'
        
        column_info.append(ColumnInfo(
            name=col['name'],
            type=col_type,
            nullable=col.get('nullable', True),
            primary_key=is_pk,
            foreign_key=fk_info,
            default=str(col.get('default', '')) if col.get('default') is not None else None
        ))
    
    # Get total count
    count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    total = count_result.scalar()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    
    # Get paginated data
    # Build ORDER BY clause using primary key or first column
    order_by_col = pk_columns[0] if pk_columns else columns[0]['name']
    query = text(f"SELECT * FROM {table_name} ORDER BY {order_by_col} LIMIT :limit OFFSET :offset")
    
    result = db.execute(query, {"limit": page_size, "offset": offset})
    rows = []
    
    for row in result:
        row_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Convert UUID, datetime, and JSON types to serializable format
            if value is None:
                row_dict[col['name']] = None
            elif isinstance(value, UUID):
                row_dict[col['name']] = str(value)
            elif isinstance(value, datetime):
                row_dict[col['name']] = value.isoformat()
            elif isinstance(value, (dict, list)):
                row_dict[col['name']] = value
            else:
                row_dict[col['name']] = value
        rows.append(row_dict)
    
    return TableDataResponse(
        table_name=table_name,
        columns=column_info,
        rows=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/api/founder/database/tables/{table_name}/rows")
def create_table_row(
    table_name: str,
    request: RowCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new row in a table."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    columns = inspector.get_columns(table_name)
    column_names = {col['name'] for col in columns}
    
    # Validate that all provided fields exist as columns
    invalid_fields = set(request.data.keys()) - column_names
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields: {', '.join(invalid_fields)}"
        )
    
    # Build INSERT statement
    valid_fields = {k: v for k, v in request.data.items() if k in column_names}
    if not valid_fields:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    
    field_names = ', '.join(valid_fields.keys())
    placeholders = ', '.join([f":{name}" for name in valid_fields.keys()])
    
    try:
        query = text(f"INSERT INTO {table_name} ({field_names}) VALUES ({placeholders}) RETURNING *")
        result = db.execute(query, valid_fields)
        db.commit()
        
        row = result.fetchone()
        if row:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, UUID):
                    row_dict[col['name']] = str(value)
                elif isinstance(value, datetime):
                    row_dict[col['name']] = value.isoformat()
                else:
                    row_dict[col['name']] = value
            return {"message": "Row created successfully", "row": row_dict}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create row: {str(e)}")


@router.put("/api/founder/database/tables/{table_name}/rows")
def update_table_row(
    table_name: str,
    request: RowUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update a row in a table. Requires 'id' field to identify the row."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get primary key columns
    pk_constraint = inspector.get_pk_constraint(table_name)
    pk_columns = pk_constraint.get('constrained_columns', []) or []
    
    if not pk_columns:
        raise HTTPException(
            status_code=400,
            detail="Table has no primary key. Cannot safely update rows."
        )
    
    # Extract primary key values from request data
    pk_values = {}
    update_values = {}
    
    for key, value in request.data.items():
        if key in pk_columns:
            pk_values[key] = value
        else:
            update_values[key] = value
    
    if not pk_values:
        raise HTTPException(
            status_code=400,
            detail=f"Primary key value(s) required: {', '.join(pk_columns)}"
        )
    
    if not update_values:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Validate that update fields exist as columns
    columns = inspector.get_columns(table_name)
    column_names = {col['name'] for col in columns}
    invalid_fields = set(update_values.keys()) - column_names
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields: {', '.join(invalid_fields)}"
        )
    
    # Build UPDATE statement with WHERE clause
    set_clauses = ', '.join([f"{name} = :{name}" for name in update_values.keys()])
    where_clauses = ' AND '.join([f"{name} = :pk_{name}" for name in pk_values.keys()])
    
    # Merge parameters
    params = update_values.copy()
    for key, value in pk_values.items():
        params[f"pk_{key}"] = value
    
    try:
        query = text(f"UPDATE {table_name} SET {set_clauses} WHERE {where_clauses} RETURNING *")
        result = db.execute(query, params)
        db.commit()
        
        updated_row = result.fetchone()
        if not updated_row:
            raise HTTPException(status_code=404, detail="Row not found or not updated")
        
        row_dict = {}
        for i, col in enumerate(columns):
            value = updated_row[i]
            if isinstance(value, UUID):
                row_dict[col['name']] = str(value)
            elif isinstance(value, datetime):
                row_dict[col['name']] = value.isoformat()
            else:
                row_dict[col['name']] = value
        
        return {"message": "Row updated successfully", "row": row_dict}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update row: {str(e)}")


@router.delete("/api/founder/database/tables/{table_name}/rows")
def delete_table_row(
    table_name: str,
    id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a row from a table. Requires 'id' query parameter."""
    if not id:
        raise HTTPException(status_code=400, detail="'id' parameter required")
    
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get primary key columns
    pk_constraint = inspector.get_pk_constraint(table_name)
    pk_columns = pk_constraint.get('constrained_columns', []) or []
    
    if not pk_columns:
        raise HTTPException(
            status_code=400,
            detail="Table has no primary key. Cannot safely delete rows."
        )
    
    # Use first primary key column (usually 'id')
    pk_column = pk_columns[0]
    
    try:
        query = text(f"DELETE FROM {table_name} WHERE {pk_column} = :id RETURNING *")
        result = db.execute(query, {"id": id})
        db.commit()
        
        deleted_row = result.fetchone()
        if not deleted_row:
            raise HTTPException(status_code=404, detail="Row not found")
        
        return {"message": "Row deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete row: {str(e)}")


@router.post("/api/founder/database/tables")
def create_table(
    request: TableCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new table. ⚠️ DANGEROUS: Schema changes can break the application."""
    inspector = inspect(engine)
    
    if request.table_name in inspector.get_table_names():
        raise HTTPException(
            status_code=400,
            detail=f"Table '{request.table_name}' already exists"
        )
    
    # Validate table name (prevent SQL injection)
    if not request.table_name.replace('_', '').isalnum():
        raise HTTPException(
            status_code=400,
            detail="Table name can only contain letters, numbers, and underscores"
        )
    
    # Build CREATE TABLE statement
    column_defs = []
    for col in request.columns:
        col_name = col.get('name', '').replace('"', '')
        col_type = col.get('type', 'TEXT').upper()
        nullable = 'NULL' if col.get('nullable', True) else 'NOT NULL'
        default = f" DEFAULT {col.get('default')}" if col.get('default') is not None else ''
        
        column_defs.append(f'"{col_name}" {col_type} {nullable}{default}')
    
    try:
        create_sql = f'CREATE TABLE "{request.table_name}" ({", ".join(column_defs)})'
        db.execute(text(create_sql))
        db.commit()
        
        return {"message": f"Table '{request.table_name}' created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create table: {str(e)}")


@router.post("/api/founder/database/tables/{table_name}/columns")
def add_table_column(
    table_name: str,
    request: ColumnAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Add a column to a table. ⚠️ DANGEROUS: Schema changes can break the application."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Check if column already exists
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    if request.column_name in existing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Column '{request.column_name}' already exists"
        )
    
    # Validate column name
    if not request.column_name.replace('_', '').isalnum():
        raise HTTPException(
            status_code=400,
            detail="Column name can only contain letters, numbers, and underscores"
        )
    
    nullable = 'NULL' if request.nullable else 'NOT NULL'
    default_clause = f" DEFAULT {request.default}" if request.default is not None else ''
    
    try:
        alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{request.column_name}" {request.column_type.upper()} {nullable}{default_clause}'
        db.execute(text(alter_sql))
        db.commit()
        
        return {"message": f"Column '{request.column_name}' added successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to add column: {str(e)}")


@router.delete("/api/founder/database/tables/{table_name}")
def delete_table(
    table_name: str,
    confirm: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a table. ⚠️ DANGEROUS: This will permanently delete all data in the table."""
    # Handle confirm parameter - FastAPI query params come as strings
    if confirm is None or confirm.lower() not in ('true', '1', 'yes'):
        raise HTTPException(
            status_code=400,
            detail="Deletion requires explicit confirmation. Set 'confirm=true' parameter."
        )
    
    inspector = inspect(engine)
    
    # Get list of tables - use exact name from database
    table_names = inspector.get_table_names()
    if table_name not in table_names:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get the exact table name as it appears in PostgreSQL (handles case sensitivity)
    # Since inspector returns the actual names, we should use the exact match
    actual_table_name = table_name  # Use the parameter which should match exactly
    
    try:
        # PostgreSQL: unquoted identifiers are lowercased, quoted preserve case
        # Try with quotes first (most common), then without if needed
        # Use CASCADE to handle foreign key constraints
        try:
            # Use the exact table name with quotes to preserve any case sensitivity
            drop_sql = text(f'DROP TABLE "{actual_table_name}" CASCADE')
            result = db.execute(drop_sql)
            logger.info(f"Executed: DROP TABLE \"{actual_table_name}\" CASCADE")
        except Exception as first_error:
            # If quoted version fails (rare), try unquoted lowercase
            logger.warning(f"Quoted drop failed for {actual_table_name}, trying unquoted: {first_error}")
            drop_sql = text(f'DROP TABLE {actual_table_name.lower()} CASCADE')
            result = db.execute(drop_sql)
            actual_table_name = actual_table_name.lower()
        
        db.commit()
        
        # Verify deletion by checking if table still exists
        fresh_inspector = inspect(engine)
        remaining_tables = fresh_inspector.get_table_names()
        if actual_table_name in remaining_tables or table_name in remaining_tables:
            logger.error(f"Table {table_name} still exists after deletion. Remaining: {remaining_tables}")
            raise HTTPException(
                status_code=500,
                detail=f"Table '{table_name}' still exists after deletion attempt. Remaining tables: {', '.join(remaining_tables[:5])}"
            )
        
        logger.info(f"Successfully deleted table: {table_name}")
        return {"message": f"Table '{table_name}' deleted successfully"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"Failed to delete table {table_name}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to delete table: {error_msg}")


@router.delete("/api/founder/database/tables/{table_name}/columns/{column_name}")
def delete_table_column(
    table_name: str,
    column_name: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a column from a table. ⚠️ DANGEROUS: This will permanently delete all data in the column."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion requires explicit confirmation. Set 'confirm=true' parameter."
        )
    
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    if column_name not in existing_columns:
        raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found")
    
    try:
        alter_sql = f'ALTER TABLE "{table_name}" DROP COLUMN "{column_name}" CASCADE'
        db.execute(text(alter_sql))
        db.commit()
        
        return {"message": f"Column '{column_name}' deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete column: {str(e)}")

