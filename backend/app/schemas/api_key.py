from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class ApiKeyCreateRequest(BaseModel):
    """Request to create a new API key scoped to a client."""
    client_id: UUID
    name: str
    expires_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"client_id": "451234c8-60a7-4e58-9b95-0e9d80f96622", "name": "OpenClaw integration", "expires_at": None}]
        }
    }


class ApiKeyCreateResponse(BaseModel):
    """Response after creating an API key. The `key` field is shown once and cannot be retrieved again."""
    id: UUID
    key: str
    key_prefix: str
    name: str
    client_id: UUID
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyListItem(BaseModel):
    """An API key summary (without the raw key)."""
    id: UUID
    key_prefix: str
    name: str
    client_id: UUID
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
