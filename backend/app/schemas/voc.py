"""
Voice of Customer (VOC) data schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID


class ProcessVocResponse(BaseModel):
    """Response schema for single process_voc row"""
    id: int
    respondent_id: str
    created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    total_rows: Optional[int] = None
    data_source: Optional[str] = None
    region: Optional[str] = None
    response_type: Optional[str] = None
    start_date: Optional[datetime] = None
    submit_date: Optional[datetime] = None
    user_type: Optional[str] = None
    dimension_ref: str
    dimension_name: Optional[str] = None
    value: Optional[str] = None
    overall_sentiment: Optional[str] = None
    topics: Optional[List[dict]] = None
    survey_metadata: Optional[dict] = None
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    client_uuid: Optional[UUID] = None
    is_favourite: Optional[bool] = None

    class Config:
        from_attributes = True


class ProcessVocListResponse(BaseModel):
    """Response for list of process_voc rows"""
    items: List[ProcessVocResponse]
    total: int

    class Config:
        from_attributes = True


class DimensionQuestionInfo(BaseModel):
    """Information about a dimension/question in process_voc"""
    dimension_ref: str
    dimension_name: Optional[str] = None
    response_count: int = 0
    question_type: Optional[str] = None


class VocSourceInfo(BaseModel):
    """Information about a data source in process_voc"""
    data_source: str
    client_uuid: Optional[UUID] = None
    client_name: Optional[str] = None
    response_count: int = 0


class VocClientInfo(BaseModel):
    """Information about a client with data in process_voc"""
    client_uuid: UUID
    client_name: Optional[str] = None
    data_source_count: int = 0


class VocProjectInfo(BaseModel):
    """Information about a project in process_voc"""
    project_name: str
    project_id: Optional[str] = None
    response_count: int = 0


class ProcessVocBulkUpdateItem(BaseModel):
    """Single item in bulk update request"""
    id: int
    project_name: Optional[str] = None
    dimension_name: Optional[str] = None
    data_source: Optional[str] = None
    client_name: Optional[str] = None
    # Allow dynamic fields via dict
    class Config:
        extra = "allow"


class ProcessVocBulkUpdateRequest(BaseModel):
    """Bulk update request for process_voc rows"""
    updates: List[ProcessVocBulkUpdateItem]


class ProcessVocBulkUpdateResponse(BaseModel):
    """Response for bulk update"""
    updated_count: int
    message: str


class ProcessVocAdminListResponse(BaseModel):
    """Paginated response for admin listing"""
    items: List[ProcessVocResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FieldMetadata(BaseModel):
    """Metadata about a field"""
    name: str
    type: str  # 'string', 'integer', 'datetime', 'text', 'json'
    nullable: bool
    category: str  # 'client', 'project', 'dimension', 'response', 'metadata', 'timestamp'
    editable: bool


class FieldMetadataResponse(BaseModel):
    """Response with all editable fields metadata"""
    fields: List[FieldMetadata]


class DynamicBulkUpdateRequest(BaseModel):
    """Dynamic bulk update request - accepts any field as key-value pairs"""
    updates: Dict[str, Optional[str]]  # field_name -> new_value (None means don't update)

