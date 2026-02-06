"""
Ad Image schemas for CRUD operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AdImageCreate(BaseModel):
    """Create a new ad image"""
    url: str = Field(..., description="Vercel Blob URL")
    filename: str = Field(..., max_length=255, description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., max_length=100, description="MIME type")
    started_running_on: Optional[datetime] = Field(None, description="Meta ad start date")
    library_id: Optional[str] = Field(None, max_length=100, description="Meta Ads Library ID")
    source_url: Optional[str] = Field(None, description="Original Meta Ads Library URL")
    import_job_id: Optional[UUID] = Field(None, description="Import job that created this")


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
    started_running_on: Optional[datetime] = None
    library_id: Optional[str] = None
    source_url: Optional[str] = None
    import_job_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class AdImageListResponse(BaseModel):
    """Paginated response for ad images list"""
    items: List[AdImageResponse]
    total: int


# Import Job schemas
class ImportJobCreate(BaseModel):
    """Create a new import job"""
    source_url: str = Field(..., description="Meta Ads Library URL to import from")


class ImportJobResponse(BaseModel):
    """Response schema for an import job"""
    id: UUID
    client_id: UUID
    user_id: Optional[UUID] = None
    source_url: str
    status: str
    total_found: int
    total_imported: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ImportJobListResponse(BaseModel):
    """Response for import jobs list"""
    items: List[ImportJobResponse]
    total: int


class ImportJobStatusResponse(BaseModel):
    """Detailed status response for an import job with recent images"""
    job: ImportJobResponse
    recent_images: List[AdImageResponse] = []
