"""
Insight tracking and management schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


class InsightOrigin(BaseModel):
    """Origin information for an insight"""
    origin_type: Literal["verbatim", "topic", "category"]
    process_voc_id: Optional[int] = None  # For verbatim origins (references ProcessVoc.id)
    project_name: Optional[str] = None
    data_source: Optional[str] = None
    dimension_ref: Optional[str] = None
    dimension_name: Optional[str] = None
    category: Optional[str] = None  # For category/topic origins
    topic_label: Optional[str] = None  # For topic origins


class InsightCreate(BaseModel):
    """Create a new insight"""
    name: str
    type: Optional[str] = None  # e.g., "headlines", "social proof", "lead-in", etc.
    application: Optional[str] = None  # Comma-separated string (e.g., "homepage, pdp, google ad") - will be converted to JSONB array
    description: Optional[str] = None
    notes: Optional[str] = None  # Formatted notes (HTML from WYSIWYG editor)
    status: Optional[str] = None  # Status: Not Started, Queued, Design, Development, QA, Testing, Win, Disproved
    origins: List[InsightOrigin] = Field(..., min_length=1)  # At least one origin required
    verbatims: Optional[List[Dict[str, Any]]] = None  # Array of pinned verbatim objects
    metadata: Optional[Dict[str, Any]] = None
    voc_json: Optional[Dict[str, Any]] = None  # Source VoC JSON object used when creating the insight


class InsightUpdate(BaseModel):
    """Update an existing insight"""
    name: Optional[str] = None
    type: Optional[str] = None
    application: Optional[str] = None  # Comma-separated string (e.g., "homepage, pdp, google ad") - will be converted to JSONB array
    description: Optional[str] = None
    notes: Optional[str] = None  # Formatted notes (HTML from WYSIWYG editor)
    status: Optional[str] = None  # Status: Not Started, Queued, Design, Development, QA, Testing, Win, Disproved
    origins: Optional[List[InsightOrigin]] = None  # Replace entire origins array
    add_origin: Optional[InsightOrigin] = None  # Append a new origin
    verbatims: Optional[List[Dict[str, Any]]] = None  # Array of pinned verbatim objects
    metadata: Optional[Dict[str, Any]] = None


class InsightResponse(BaseModel):
    """Response schema for an insight"""
    id: UUID
    client_id: UUID
    name: str
    type: Optional[str] = None  # e.g., "headlines", "social proof", "lead-in", etc.
    application: Optional[List[str]] = None  # JSONB array of applications (e.g., ["homepage", "pdp", "google ad"])
    description: Optional[str] = None
    notes: Optional[str] = None  # Formatted notes (HTML from WYSIWYG editor)
    status: Optional[str] = None  # Status: Not Started, Queued, Design, Development, QA, Testing, Win, Disproved
    origins: List[InsightOrigin] = Field(default_factory=list)
    verbatims: Optional[List[Dict[str, Any]]] = Field(default_factory=list)  # Array of pinned verbatim objects
    metadata: Optional[Dict[str, Any]] = None
    voc_json: Optional[Dict[str, Any]] = None  # Source VoC JSON object used when creating the insight
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle JSONB origins array"""
        # Use getattr to handle cases where status column might not exist yet (before migration)
        status = getattr(obj, 'status', None) or 'Not Started'
        # Convert application JSONB array to list (it's already a list if JSONB, or None)
        application_value = obj.application
        if application_value is not None and not isinstance(application_value, list):
            # Handle legacy text format (shouldn't happen after migration, but be safe)
            if isinstance(application_value, str):
                application_value = [app.strip() for app in application_value.split(',') if app.strip()]
            else:
                application_value = None
        data = {
            'id': obj.id,
            'client_id': obj.client_id,
            'name': obj.name,
            'type': obj.type,
            'application': application_value,
            'description': obj.description,
            'notes': obj.notes,
            'status': status,
            'metadata': obj.meta_data or {},
            'verbatims': obj.verbatims or [],
            'voc_json': getattr(obj, 'voc_json', None),
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'created_by': obj.created_by,
            'origins': [InsightOrigin(**origin) for origin in (obj.origins or [])],
        }
        return cls(**data)

    class Config:
        from_attributes = True


class InsightListResponse(BaseModel):
    """Paginated response for insights list"""
    items: List[InsightResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

