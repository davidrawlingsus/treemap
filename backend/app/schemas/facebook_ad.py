"""
Facebook Ad schemas for CRUD operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class FacebookAdCreate(BaseModel):
    """Create a new Facebook ad"""
    primary_text: str = Field(..., description="Main ad copy text")
    headline: str = Field(..., max_length=255, description="Ad headline")
    description: Optional[str] = Field(None, description="Ad description")
    call_to_action: str = Field(..., max_length=50, description="CTA button (SHOP_NOW, LEARN_MORE, etc.)")
    destination_url: Optional[str] = Field(None, description="Link URL")
    image_hash: Optional[str] = Field(None, description="Image prompt from LLM")
    voc_evidence: Optional[List[str]] = Field(default_factory=list, description="Array of VoC quotes")
    full_json: Dict[str, Any] = Field(..., description="Complete original JSON for FB API")
    insight_id: Optional[UUID] = Field(None, description="Link to insight if saved to one")
    action_id: Optional[UUID] = Field(None, description="Link to source action/history item")
    status: Optional[str] = Field(default="draft", description="Ad status: draft, ready, exported")


class FacebookAdUpdate(BaseModel):
    """Update an existing Facebook ad"""
    primary_text: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    call_to_action: Optional[str] = None
    destination_url: Optional[str] = None
    image_hash: Optional[str] = None
    image_url: Optional[str] = Field(None, description="Image URL from ad_images inventory")
    voc_evidence: Optional[List[str]] = None
    status: Optional[str] = None


class FacebookAdResponse(BaseModel):
    """Response schema for a Facebook ad"""
    id: UUID
    client_id: UUID
    insight_id: Optional[UUID] = None
    action_id: Optional[UUID] = None
    primary_text: str
    headline: str
    description: Optional[str] = None
    call_to_action: str
    destination_url: Optional[str] = None
    image_hash: Optional[str] = None
    voc_evidence: Optional[List[str]] = Field(default_factory=list)
    full_json: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class FacebookAdListResponse(BaseModel):
    """Paginated response for Facebook ads list"""
    items: List[FacebookAdResponse]
    total: int
