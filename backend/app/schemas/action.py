"""
Action schemas for LLM-generated actions.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID


class ActionCreate(BaseModel):
    """Create a new action record"""
    prompt_id: UUID = Field(..., description="ID of the prompt used")
    prompt_text_sent: str = Field(..., description="The actual prompt text that was sent to the LLM")
    actions: Dict[str, Any] = Field(..., description="LLM response data (JSONB)")
    client_id: UUID = Field(..., description="ID of the client this action was generated for")
    insight_ids: List[UUID] = Field(default_factory=list, description="Array of insight UUIDs that were used")


class ActionResponse(BaseModel):
    """Response schema for an action"""
    id: UUID
    prompt_id: UUID
    prompt_text_sent: str
    actions: Dict[str, Any]
    client_id: UUID
    insight_ids: List[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

