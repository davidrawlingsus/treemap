"""
CSV upload and mapping schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID


class CsvColumnMapping(BaseModel):
    """Schema for column configuration"""
    column_name: str
    is_tta: bool
    question_text: Optional[str] = None
    question_purpose: Optional[str] = None


class CsvUploadResponse(BaseModel):
    """Response schema for CSV upload"""
    column_headers: List[str]
    sample_rows: List[Dict[str, Any]]
    row_count: int
    project_id: str
    data_source_id: str
    csv_data: List[Dict[str, Any]]
    project_name: Optional[str] = None
    data_source: Optional[str] = None


class CsvColumnMappingRequest(BaseModel):
    """Request schema for saving mapped CSV data"""
    client_uuid: UUID
    project_name: str
    project_id: str
    data_source: str
    data_source_id: str
    column_mappings: List[CsvColumnMapping]
    csv_data: List[Dict[str, Any]]


class CsvSaveResponse(BaseModel):
    """Response schema for CSV save operation"""
    rows_created: int
    message: str

