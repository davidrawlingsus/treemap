"""
Data source and dimension schemas.
"""
from pydantic import BaseModel, Field, model_serializer
from typing import Any, Union, Optional, List
from datetime import datetime
from uuid import UUID


class DataSourceCreate(BaseModel):
    name: str
    client_id: Optional[UUID] = None
    source_name: Optional[str] = None
    source_type: str = "intercom"
    source_format: str = "intercom_mrt"
    raw_data: Union[dict, list]  # Can be dict or list


class DataSourceResponse(BaseModel):
    id: UUID
    name: str
    client_id: Optional[UUID] = None
    source_name: Optional[str] = None
    source_type: str
    source_format: str
    is_normalized: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Include client name in response for convenience
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


class DataSourceDetail(DataSourceResponse):
    normalized_data: Optional[Union[dict, list]] = None
    raw_data: Optional[Union[dict, list]] = None
    
    @model_serializer
    def serialize_model(self):
        """Custom serializer to return normalized_data as raw_data for backward compatibility"""
        data = {
            'id': self.id,
            'name': self.name,
            'client_id': self.client_id,
            'source_name': self.source_name,
            'source_type': self.source_type,
            'source_format': self.source_format,
            'is_normalized': self.is_normalized,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'client_name': self.client_name,
        }
        
        # Use normalized_data if available, otherwise fall back to raw_data
        if self.normalized_data is not None:
            data['raw_data'] = self.normalized_data
        elif self.raw_data is not None:
            data['raw_data'] = self.raw_data
        else:
            data['raw_data'] = []
            
        return data

    class Config:
        from_attributes = True


class QuestionInfo(BaseModel):
    """Information about a question in survey data"""
    ref_key: str
    sample_text: Optional[str] = None
    response_count: int = 0
    custom_name: Optional[str] = None  # Custom dimension name if assigned


class DataSourceWithQuestions(DataSourceResponse):
    """Data source with detected questions"""
    questions: List[QuestionInfo] = []

    class Config:
        from_attributes = True


class DimensionNameCreate(BaseModel):
    """Create or update a dimension name"""
    ref_key: str
    custom_name: str


class DimensionNameBatchUpdate(BaseModel):
    """Batch update multiple dimension names for a data source"""
    dimension_names: List[DimensionNameCreate]


class DimensionNameResponse(BaseModel):
    """Response for dimension name"""
    id: UUID
    data_source_id: UUID
    ref_key: str
    custom_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

