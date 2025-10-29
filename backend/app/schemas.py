from pydantic import BaseModel, Field, model_serializer
from typing import Any, Union, Optional, List, Dict
from datetime import datetime
from uuid import UUID


# Client Schemas
class ClientCreate(BaseModel):
    name: str
    slug: str
    is_active: bool = True
    settings: Optional[dict] = {}


class ClientResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Data Source Schemas
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


# Dimension Name Schemas
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


# Growth Idea Schemas
class GrowthIdeaCreate(BaseModel):
    """Create a growth idea"""
    client_id: UUID
    data_source_id: UUID
    dimension_ref_key: str
    dimension_name: Optional[str] = None
    idea_text: str
    status: str = "pending"
    priority: Optional[int] = None
    context_data: Optional[dict] = None
    generation_prompt: Optional[str] = None


class GrowthIdeaUpdate(BaseModel):
    """Update a growth idea's status or priority"""
    status: Optional[str] = None
    priority: Optional[int] = None


class GrowthIdeaResponse(BaseModel):
    """Response for growth idea"""
    id: UUID
    client_id: UUID
    data_source_id: UUID
    dimension_ref_key: str
    dimension_name: Optional[str] = None
    idea_text: str
    status: str
    priority: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Optional enrichment fields
    client_name: Optional[str] = None
    data_source_name: Optional[str] = None

    class Config:
        from_attributes = True


class GrowthIdeaGenerateRequest(BaseModel):
    """Parameters for generating ideas (optional, uses defaults if not provided)"""
    max_ideas: Optional[int] = None


class GrowthIdeaGenerateResponse(BaseModel):
    """Response from idea generation"""
    ideas: List[GrowthIdeaResponse]
    total_generated: int


class TopicSpecificIdeaRequest(BaseModel):
    """Request for generating topic-specific ideas"""
    topic_name: str
    category_name: Optional[str] = None
    max_ideas: Optional[int] = None


class ClientGrowthIdeasStats(BaseModel):
    """Statistics for client's growth ideas"""
    total_ideas: int
    accepted_count: int
    pending_count: int
    rejected_count: int
    by_data_source: Dict[str, int]
    by_priority: Dict[str, int]

