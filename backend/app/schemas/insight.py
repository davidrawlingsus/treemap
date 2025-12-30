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
    type: str
    application: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None  # Formatted notes (HTML from WYSIWYG editor)
    status: Optional[str] = None  # Status: Not Started, Queued, Design, Development, QA, Testing, Win, Disproved
    origins: List[InsightOrigin] = Field(..., min_length=1)  # At least one origin required
    verbatims: Optional[List[Dict[str, Any]]] = None  # Array of pinned verbatim objects
    metadata: Optional[Dict[str, Any]] = None


class InsightUpdate(BaseModel):
    """Update an existing insight"""
    name: Optional[str] = None
    type: Optional[str] = None
    application: Optional[str] = None
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
    type: str
    application: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None  # Formatted notes (HTML from WYSIWYG editor)
    status: Optional[str] = None  # Status: Not Started, Queued, Design, Development, QA, Testing, Win, Disproved
    origins: List[InsightOrigin] = Field(default_factory=list)
    verbatims: Optional[List[Dict[str, Any]]] = Field(default_factory=list)  # Array of pinned verbatim objects
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle JSONB origins array"""
        # Use getattr to handle cases where status column might not exist yet (before migration)
        status = getattr(obj, 'status', None) or 'Not Started'
        data = {
            'id': obj.id,
            'client_id': obj.client_id,
            'name': obj.name,
            'type': obj.type,
            'application': obj.application,
            'description': obj.description,
            'notes': obj.notes,
            'status': status,
            'metadata': obj.meta_data or {},
            'verbatims': obj.verbatims or [],
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

