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
    business_summary: Optional[str] = None
    client_url: Optional[str] = None
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


# Resolve forward references
AuthorizedDomainResponse.model_rebuild()
AuthorizedEmailResponse.model_rebuild()

