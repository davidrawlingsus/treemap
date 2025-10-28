from pydantic import BaseModel, Field, model_serializer
from typing import Any, Union, Optional
from datetime import datetime
from uuid import UUID


class DataSourceCreate(BaseModel):
    name: str
    source_type: str = "intercom"
    source_format: str = "intercom_mrt"
    raw_data: Union[dict[str, Any], list[Any]]  # Can be dict or list


class DataSourceResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    source_format: str
    is_normalized: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class DataSourceDetail(DataSourceResponse):
    normalized_data: Optional[Union[dict[str, Any], list[Any]]] = None
    raw_data: Optional[Union[dict[str, Any], list[Any]]] = None
    
    @model_serializer
    def serialize_model(self):
        """Custom serializer to return normalized_data as raw_data for backward compatibility"""
        data = {
            'id': self.id,
            'name': self.name,
            'source_type': self.source_type,
            'source_format': self.source_format,
            'is_normalized': self.is_normalized,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
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

