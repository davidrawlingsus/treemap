"""
Action schemas for LLM-generated actions.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Optional
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
    # Include prompt details if available
    prompt_name: Optional[str] = None
    prompt_version: Optional[int] = None
    prompt_system_message: Optional[str] = None

    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm_with_prompt(cls, action):
        """Create ActionResponse from Action with prompt relationship loaded"""
        data = {
            'id': action.id,
            'prompt_id': action.prompt_id,
            'prompt_text_sent': action.prompt_text_sent,
            'actions': action.actions,
            'client_id': action.client_id,
            'insight_ids': action.insight_ids,
            'created_at': action.created_at,
        }
        # Add prompt details if relationship is loaded
        if hasattr(action, 'prompt') and action.prompt:
            data['prompt_name'] = action.prompt.name
            data['prompt_version'] = action.prompt.version
            data['prompt_system_message'] = action.prompt.system_message
        return cls(**data)

