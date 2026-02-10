"""
Schemas for Creative MRI report: request (ads or ad_library_import_id) and response.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID


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
