"""
Schemas for Ad Library imports (copy only, for VOC comparison).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AdLibraryMediaResponse(BaseModel):
    """Single media item (video or image) from an ad."""
    id: UUID
    ad_id: UUID
    media_type: str  # image | video
    url: str
    poster_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


class AdLibraryAdResponse(BaseModel):
    """Single ad from an Ad Library import (copy + metadata + media)."""
    id: UUID
    import_id: UUID
    primary_text: str
    headline: Optional[str] = None
    description: Optional[str] = None
    library_id: Optional[str] = None
    started_running_on: Optional[str] = None
    ad_delivery_start_time: Optional[str] = None
    ad_delivery_end_time: Optional[str] = None
    ad_format: Optional[str] = None  # video | image | carousel
    cta: Optional[str] = None
    destination_url: Optional[str] = None
    media_thumbnail_url: Optional[str] = None
    status: Optional[str] = None
    platforms: Optional[List[str]] = None
    ads_using_creative_count: Optional[int] = None
    page_name: Optional[str] = None
    page_url: Optional[str] = None
    page_profile_image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdLibraryAdDetailResponse(AdLibraryAdResponse):
    """Ad with media items."""
    media_items: List[AdLibraryMediaResponse] = []


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
    """Ad Library import with full list of ads (including media)."""
    id: UUID
    client_id: UUID
    source_url: str
    imported_at: datetime
    ads: List[AdLibraryAdDetailResponse] = []

    class Config:
        from_attributes = True


class AdLibraryImportListResponse(BaseModel):
    """List of imports for a client."""
    items: List[AdLibraryImportResponse]
    total: int


class AdLibraryImportStartedResponse(BaseModel):
    """Response when import is started in the background (202)."""
    status: str = "started"
    message: str = "Import started. This may take 1–2 minutes. Refresh the list to see the new import."


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
