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
    """A survey dimension/question with its response count."""
    dimension_ref: str
    dimension_name: Optional[str] = None
    response_count: int = 0
    question_type: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"dimension_ref": "ref_ljwfv", "dimension_name": "What did you like most?", "response_count": 1234, "question_type": "open_text"}]
        }
    }


class VocSourceInfo(BaseModel):
    """A data source (e.g. trustpilot, email_survey) with its response count."""
    data_source: str
    client_uuid: Optional[UUID] = None
    client_name: Optional[str] = None
    response_count: int = 0

    model_config = {
        "json_schema_extra": {
            "examples": [{"data_source": "trustpilot", "client_uuid": "451234c8-60a7-4e58-9b95-0e9d80f96622", "client_name": "Acme Co", "response_count": 515}]
        }
    }


class VocClientInfo(BaseModel):
    """A client accessible to the current user, with data source count."""
    client_uuid: UUID
    client_name: Optional[str] = None
    data_source_count: int = 0
    logo_url: Optional[str] = None
    header_color: Optional[str] = None
    is_lead: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [{"client_uuid": "451234c8-60a7-4e58-9b95-0e9d80f96622", "client_name": "Acme Co", "data_source_count": 3, "logo_url": None, "header_color": "#1a73e8"}]
        }
    }


class VocProjectInfo(BaseModel):
    """A project containing VOC data, with its response count."""
    project_name: str
    project_id: Optional[str] = None
    response_count: int = 0

    model_config = {
        "json_schema_extra": {
            "examples": [{"project_name": "Q1 2026 Survey", "project_id": "a3b4c5d6", "response_count": 2500}]
        }
    }


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


# VOC summary for comparison (categories -> topics -> counts + sample verbatims)
class VocSummaryTopic(BaseModel):
    """Topic within a category with verbatim count and samples"""
    label: str
    code: Optional[str] = None
    verbatim_count: int
    sample_verbatims: List[str] = []


class VocSummaryCategory(BaseModel):
    """Category with its topics"""
    name: str
    topics: List[VocSummaryTopic] = []


class VocSummaryResponse(BaseModel):
    """Hierarchical VOC summary: categories containing topics with sample verbatims."""
    categories: List[VocSummaryCategory] = []
    total_verbatims: int = 0

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "total_verbatims": 515,
                "categories": [{
                    "name": "Product Quality",
                    "topics": [{
                        "label": "Effective results",
                        "code": "T001",
                        "verbatim_count": 42,
                        "sample_verbatims": ["Really impressed with how well it works", "Noticed a difference within days"]
                    }]
                }]
            }]
        }
    }

