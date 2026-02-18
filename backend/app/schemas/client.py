"""
Client and authorized domain schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


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


class ClientResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    ad_library_only: Optional[bool] = False
    business_summary: Optional[str] = None
    client_url: Optional[str] = None
    logo_url: Optional[str] = None
    header_color: Optional[str] = None
    tone_of_voice: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AuthorizedDomainResponse(AuthorizedDomainBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    clients: List[ClientResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AuthorizedEmailBase(BaseModel):
    email: str = Field(..., description="Email address (e.g. user@example.com)")
    description: Optional[str] = Field(
        default=None, description="Optional description for internal reference"
    )


class AuthorizedEmailCreate(AuthorizedEmailBase):
    client_ids: List[UUID] = Field(
        default_factory=list,
        description="Clients to associate with this authorized email",
    )


class AuthorizedEmailUpdate(AuthorizedEmailBase):
    client_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional list of clients to replace existing associations",
    )


class AuthorizedEmailResponse(AuthorizedEmailBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    clients: List[ClientResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    name: str
    slug: str
    is_active: bool = True
    settings: dict = {}
    ad_library_only: bool = False


class ClientLogoUpdate(BaseModel):
    logo_url: str = Field(..., description="URL of the client logo")
    header_color: str = Field(..., description="Hex color for header background (e.g. #FFFFFF)")


class ClientSettingsUpdate(BaseModel):
    """Schema for updating client-facing settings (logo, business context, tone of voice)"""
    client_url: Optional[str] = Field(default=None, description="Brand website URL")
    logo_url: Optional[str] = Field(default=None, description="URL of the client logo")
    header_color: Optional[str] = Field(default=None, description="Hex color for header background (e.g. #FFFFFF)")
    business_summary: Optional[str] = Field(default=None, description="Business context/summary for AI prompts")
    tone_of_voice: Optional[str] = Field(default=None, description="Brand tone of voice for consistent ad copy")


# Product Context schemas
class ProductContextExtractRequest(BaseModel):
    """Request to extract product context from a PDP URL"""
    url: str = Field(..., description="PDP URL to fetch and extract from")


class ProductContextExtractResponse(BaseModel):
    """Response from product context extraction (not persisted)"""
    name: str = Field(..., description="Product name extracted")
    context_text: str = Field(..., description="Extracted product context")
    source_url: str = Field(..., description="PDP URL used")


class ProductContextCreate(BaseModel):
    """Create a new product context"""
    name: str = Field(..., description="Product name")
    context_text: str = Field(default="", description="Product context text")
    source_url: Optional[str] = Field(default=None, description="PDP URL source")


class ProductContextUpdate(BaseModel):
    """Update an existing product context"""
    name: Optional[str] = Field(default=None, description="Product name")
    context_text: Optional[str] = Field(default=None, description="Product context text")
    source_url: Optional[str] = Field(default=None, description="PDP URL source")


class ProductContextResponse(BaseModel):
    """Product context response"""
    id: UUID
    client_id: UUID
    name: str
    context_text: Optional[str] = None
    source_url: Optional[str] = None
    is_live: bool
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Resolve forward references
AuthorizedDomainResponse.model_rebuild()
AuthorizedEmailResponse.model_rebuild()

