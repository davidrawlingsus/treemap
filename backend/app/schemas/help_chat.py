from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class HelpChatEnsureConversationRequest(BaseModel):
    conversation_id: Optional[UUID] = None
    visitor_token: Optional[str] = Field(default=None, max_length=128)
    visitor_name: Optional[str] = Field(default=None, max_length=255)
    visitor_email: Optional[str] = Field(default=None, max_length=255)
    source_url: Optional[str] = None
    source_path: Optional[str] = Field(default=None, max_length=255)
    source_title: Optional[str] = Field(default=None, max_length=255)
    referrer_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HelpChatMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)
    client_message_id: Optional[str] = Field(default=None, max_length=128)


class HelpChatMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_type: str
    sender_label: Optional[str] = None
    body: str
    slack_ts: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HelpChatConversationResponse(BaseModel):
    id: UUID
    visitor_token: str
    status: str
    source_url: Optional[str] = None
    source_path: Optional[str] = None
    source_title: Optional[str] = None
    referrer_url: Optional[str] = None
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None
    is_authenticated_user: bool = False
    messages: list[HelpChatMessageResponse] = Field(default_factory=list)


class HelpChatWebhookResponse(BaseModel):
    ok: bool = True
