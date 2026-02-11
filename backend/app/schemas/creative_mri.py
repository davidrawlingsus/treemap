"""
Schemas for Creative MRI report: request (ads or ad_library_import_id) and response.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class CreativeMRIAdInput(BaseModel):
    """Minimal ad input for Creative MRI."""
    id: Optional[str] = None
    headline: Optional[str] = None
    primary_text: Optional[str] = None
    cta: Optional[str] = None
    destination_url: Optional[str] = None
    ad_format: Optional[str] = None
    ad_delivery_start_time: Optional[str] = None
    ad_delivery_end_time: Optional[str] = None
    media_thumbnail_url: Optional[str] = None


class CreativeMRIRequest(BaseModel):
    """Request: either inline ads or client_id + ad_library_import_id to load from DB."""
    ads: Optional[List[CreativeMRIAdInput]] = Field(None, description="Inline ad list; if omitted, use ad_library_import_id + client_id")
    client_id: Optional[UUID] = Field(None, description="Client UUID when loading from Ad Library import")
    ad_library_import_id: Optional[UUID] = Field(None, description="Ad Library import UUID; use latest for client if omitted")


class CreativeMRIResponse(BaseModel):
    """Report payload: meta, executive_summary, ads, tear_down. Allow extra fields for subscores/llm."""
    class Config:
        extra = "allow"

    meta: dict
    executive_summary: dict
    ads: List[dict]
    tear_down: dict


class CreativeMRIReportResponse(BaseModel):
    """Stored report: status and optional full report when complete."""
    id: UUID
    client_id: UUID
    ad_library_import_id: Optional[UUID] = None
    status: str
    report: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class CreativeMRIReportListItem(BaseModel):
    """Minimal report info for list view (no full report JSON)."""
    id: UUID
    client_id: UUID
    ad_library_import_id: Optional[UUID] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class CreativeMRIReportListResponse(BaseModel):
    """List of reports for a client."""
    items: List[CreativeMRIReportListItem]


class CreativeMRIReportHistoryItem(BaseModel):
    """Report list item for History tab (includes client name)."""
    id: UUID
    client_id: UUID
    client_name: str
    status: str
    ad_count: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class CreativeMRIReportHistoryResponse(BaseModel):
    """List of all reports across clients for History tab."""
    items: List[CreativeMRIReportHistoryItem]
