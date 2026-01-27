"""
Ad Image schemas for CRUD operations.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class AdImageCreate(BaseModel):
    """Create a new ad image"""
    url: str = Field(..., description="Vercel Blob URL")
    filename: str = Field(..., max_length=255, description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., max_length=100, description="MIME type")


class AdImageResponse(BaseModel):
    """Response schema for an ad image"""
    id: UUID
    client_id: UUID
    url: str
    filename: str
    file_size: int
    content_type: str
    uploaded_at: datetime
    uploaded_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class AdImageListResponse(BaseModel):
    """Paginated response for ad images list"""
    items: list[AdImageResponse]
    total: int
