from pydantic import BaseModel, Field, model_serializer
from typing import Any, Union, Optional, List, Dict
from datetime import datetime
from uuid import UUID


# Authorized Domain Schemas
class AuthorizedDomainBase(BaseModel):
    domain: str = Field(..., description="Domain name (e.g. example.com)")
    description: Optional[str] = Field(
        default=None, description="Optional description for internal reference"
    )


class AuthorizedDomainCreate(AuthorizedDomainBase):
    client_ids: List[UUID] = Field(
        default_factory=list,
        description="Clients to associate with this authorized domain",
    )


class AuthorizedDomainUpdate(AuthorizedDomainBase):
    client_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional list of clients to replace existing associations",
    )


class AuthorizedDomainResponse(AuthorizedDomainBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    clients: List["ClientResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


# Client Schemas
class ClientCreate(BaseModel):
    name: str
    slug: str
    is_active: bool = True
    settings: dict = {}


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


# Authentication Schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[str] = None


class UserLogin(BaseModel):
    """Login request"""
    email: str
    password: str


class MagicLinkRequest(BaseModel):
    """Request payload for initiating a magic-link email."""
    email: str


class MagicLinkVerifyRequest(BaseModel):
    """Request payload for verifying a magic-link token."""
    email: str
    token: str


class ImpersonateRequest(BaseModel):
    """Payload for founder impersonation."""
    user_id: UUID


class FounderUserMembership(BaseModel):
    """Membership details for founder user insights."""
    client: ClientResponse
    role: str
    status: str
    provisioned_at: Optional[datetime] = None
    provisioning_method: Optional[str] = None
    joined_at: Optional[datetime] = None


class UserResponse(BaseModel):
    """User response"""
    id: UUID
    email: str
    name: Optional[str] = None
    is_founder: bool
    is_active: bool
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    last_magic_link_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserWithClients(UserResponse):
    """User response with accessible clients"""
    accessible_clients: List[ClientResponse] = []

    class Config:
        from_attributes = True


class FounderUserSummary(UserResponse):
    """Founder view of a user with memberships"""
    email_domain: str
    memberships: List[FounderUserMembership] = Field(default_factory=list)

    class Config:
        from_attributes = True


# Resolve forward references
AuthorizedDomainResponse.model_rebuild()


# ProcessVoc Schemas
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


# Database Management Schemas
class ColumnInfo(BaseModel):
    """Information about a database column"""
    name: str
    type: str
    nullable: bool
    primary_key: bool = False
    foreign_key: Optional[str] = None
    default: Optional[Any] = None


class TableInfo(BaseModel):
    """Information about a database table"""
    name: str
    row_count: Optional[int] = None
    columns: List[ColumnInfo] = Field(default_factory=list)


class TableDataResponse(BaseModel):
    """Paginated response for table data"""
    table_name: str
    columns: List[ColumnInfo]
    rows: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


class RowCreateRequest(BaseModel):
    """Request to create a new row"""
    data: Dict[str, Any]


class RowUpdateRequest(BaseModel):
    """Request to update a row"""
    data: Dict[str, Any]


class TableCreateRequest(BaseModel):
    """Request to create a new table"""
    table_name: str
    columns: List[Dict[str, Any]]  # name, type, nullable, etc.


class ColumnAddRequest(BaseModel):
    """Request to add a column to a table"""
    column_name: str
    column_type: str
    nullable: bool = True
    default: Optional[Any] = None

