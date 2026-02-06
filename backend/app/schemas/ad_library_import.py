"""
Schemas for Ad Library imports (copy only, for VOC comparison).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AdLibraryAdResponse(BaseModel):
    """Single ad from an Ad Library import."""
    id: UUID
    import_id: UUID
    primary_text: str
    headline: Optional[str] = None
    description: Optional[str] = None
    library_id: Optional[str] = None
    started_running_on: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdLibraryImportResponse(BaseModel):
    """One Ad Library import run with ad count."""
    id: UUID
    client_id: UUID
    source_url: str
    imported_at: datetime
    ad_count: int = 0

    class Config:
        from_attributes = True


class AdLibraryImportDetailResponse(BaseModel):
    """Ad Library import with full list of ads."""
    id: UUID
    client_id: UUID
    source_url: str
    imported_at: datetime
    ads: List[AdLibraryAdResponse] = []

    class Config:
        from_attributes = True


class AdLibraryImportListResponse(BaseModel):
    """List of imports for a client."""
    items: List[AdLibraryImportResponse]
    total: int


class AdLibraryImportFromUrlRequest(BaseModel):
    """Request to import ad copy from a Meta Ads Library URL."""
    source_url: str = Field(..., description="Meta Ads Library URL with view_all_page_id")
    max_scrolls: int = Field(default=5, ge=1, le=20, description="Scrolls to load more ads")


class VocAdsComparisonRequest(BaseModel):
    """Request to run VOC vs Ads comparison."""
    ad_source: str = Field(
        ...,
        description="Which ads to compare: in_app, ad_library, or both"
    )
    ad_library_import_id: Optional[UUID] = Field(
        None,
        description="Required when ad_source is ad_library or both; use latest import if omitted for ad_library"
    )
    data_source: Optional[str] = None
    dimension_ref: Optional[str] = None
    dimension_refs: Optional[List[str]] = Field(
        None,
        description="Limit comparison to these VOC dimension refs (questions). Omit for all dimensions."
    )
    project_name: Optional[str] = None
