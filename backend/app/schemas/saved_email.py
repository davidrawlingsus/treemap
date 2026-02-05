"""
SavedEmail schemas for CRUD operations.
Follows the pattern established by FacebookAd schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class SavedEmailCreate(BaseModel):
    """Create a new saved email"""
    email_type: Optional[str] = Field(None, max_length=100, description="Email type for filtering")
    subject_line: str = Field(..., max_length=255, description="Email subject line")
    preview_text: Optional[str] = Field(None, max_length=255, description="Email preview text")
    from_name: Optional[str] = Field(None, max_length=100, description="Sender name")
    headline: Optional[str] = Field(None, max_length=255, description="Email headline/greeting")
    body_text: str = Field(..., description="Main email body text")
    discount_code: Optional[str] = Field(None, max_length=50, description="Discount code to display")
    social_proof: Optional[str] = Field(None, description="Customer testimonial")
    cta_text: Optional[str] = Field(None, max_length=100, description="CTA button text")
    cta_url: Optional[str] = Field(None, description="CTA destination URL")
    sequence_position: Optional[int] = Field(None, description="Position in email sequence")
    send_delay_hours: Optional[int] = Field(None, description="Hours after trigger to send")
    voc_evidence: Optional[List[str]] = Field(default_factory=list, description="Array of VoC quotes")
    strategic_intent: Optional[str] = Field(None, description="Strategic intent description")
    full_json: Dict[str, Any] = Field(..., description="Complete original JSON for Klaviyo export")
    action_id: Optional[UUID] = Field(None, description="Link to source action/history item")
    status: Optional[str] = Field(default="draft", description="Email status: draft, ready, exported")


class SavedEmailUpdate(BaseModel):
    """Update an existing saved email"""
    email_type: Optional[str] = None
    subject_line: Optional[str] = None
    preview_text: Optional[str] = None
    from_name: Optional[str] = None
    headline: Optional[str] = None
    body_text: Optional[str] = None
    discount_code: Optional[str] = None
    social_proof: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    sequence_position: Optional[int] = None
    send_delay_hours: Optional[int] = None
    voc_evidence: Optional[List[str]] = None
    strategic_intent: Optional[str] = None
    status: Optional[str] = None
    # These fields are stored in full_json (same pattern as FacebookAd)
    image_url: Optional[str] = Field(None, description="Image URL from images inventory")
    sequence_badge_text: Optional[str] = Field(None, description="Custom sequence badge text")


class SavedEmailResponse(BaseModel):
    """Response schema for a saved email"""
    id: UUID
    client_id: UUID
    action_id: Optional[UUID] = None
    email_type: Optional[str] = None
    subject_line: str
    preview_text: Optional[str] = None
    from_name: Optional[str] = None
    headline: Optional[str] = None
    body_text: str
    discount_code: Optional[str] = None
    social_proof: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    sequence_position: Optional[int] = None
    send_delay_hours: Optional[int] = None
    voc_evidence: Optional[List[str]] = Field(default_factory=list)
    strategic_intent: Optional[str] = None
    full_json: Dict[str, Any]
    status: str
    klaviyo_campaign_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class SavedEmailListResponse(BaseModel):
    """Paginated response for saved emails list"""
    items: List[SavedEmailResponse]
    total: int


class EmailPositionUpdate(BaseModel):
    """Single email position update for batch reorder"""
    id: UUID = Field(..., description="Email UUID")
    sequence_position: int = Field(..., description="New sequence position")
    send_delay_hours: Optional[int] = Field(None, description="New send delay in hours (optional)")


class BatchReorderRequest(BaseModel):
    """Request body for batch reorder endpoint"""
    updates: List[EmailPositionUpdate] = Field(..., description="List of position updates")


class BatchReorderResponse(BaseModel):
    """Response for batch reorder endpoint"""
    updated_count: int = Field(..., description="Number of emails updated")
    emails: List[SavedEmailResponse] = Field(..., description="Updated emails")
