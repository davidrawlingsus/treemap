"""
Authentication and user-related schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID

if TYPE_CHECKING:
    from .client import ClientResponse


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
    client: "ClientResponse"
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
    accessible_clients: List["ClientResponse"] = []

    class Config:
        from_attributes = True


class FounderUserSummary(UserResponse):
    """Founder view of a user with memberships"""
    email_domain: str
    memberships: List[FounderUserMembership] = Field(default_factory=list)

    class Config:
        from_attributes = True

