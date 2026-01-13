"""
Action schemas for LLM-generated actions.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID


class ActionCreate(BaseModel):
    """Create a new action record"""
    prompt_id: UUID = Field(..., description="ID of the prompt used")
    prompt_text_sent: str = Field(..., description="The actual prompt text that was sent to the LLM")
    actions: Dict[str, Any] = Field(..., description="LLM response data (JSONB)")
    client_id: UUID = Field(..., description="ID of the client this action was generated for")
    insight_ids: List[UUID] = Field(default_factory=list, description="Array of insight UUIDs that were used")
    origin: Optional[Dict[str, Any]] = Field(None, description="Origin metadata (same structure as insight origins)")
    voc_json: Optional[Dict[str, Any]] = Field(None, description="Source VoC JSON object used when executing the prompt")


class ActionResponse(BaseModel):
    """Response schema for an action"""
    id: UUID
    prompt_id: UUID
    prompt_text_sent: str
    actions: Dict[str, Any]
    client_id: UUID
    insight_ids: List[UUID]
    origin: Optional[Dict[str, Any]] = None
    voc_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    # Include prompt details if available
    prompt_name: Optional[str] = None
    prompt_version: Optional[int] = None
    prompt_system_message: Optional[str] = None
    prompt_purpose: Optional[str] = None

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
            'origin': getattr(action, 'origin', None),
            'voc_json': getattr(action, 'voc_json', None),
            'created_at': action.created_at,
        }
        # Add prompt details if relationship is loaded
        if hasattr(action, 'prompt') and action.prompt:
            data['prompt_name'] = action.prompt.name
            data['prompt_version'] = action.prompt.version
            data['prompt_system_message'] = action.prompt.system_message
            data['prompt_purpose'] = action.prompt.prompt_purpose
        return cls(**data)


class ClientActionResponse(BaseModel):
    """Response schema for a client action (simplified for history view)"""
    id: UUID
    prompt_id: UUID
    prompt_purpose: Optional[str] = None
    created_at: datetime
    content_preview: Optional[str] = None  # First 200 chars of content
    origin: Optional[Dict[str, Any]] = None  # Origin metadata for display
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_action_with_prompt(cls, action):
        """Create ClientActionResponse from Action with prompt relationship loaded"""
        content_preview = None
        if action.actions and isinstance(action.actions, dict):
            content = action.actions.get("content", "")
            if content:
                content_preview = content[:200] + ("..." if len(content) > 200 else "")
        
        prompt_purpose = None
        if hasattr(action, 'prompt') and action.prompt:
            prompt_purpose = action.prompt.prompt_purpose
        
        return cls(
            id=action.id,
            prompt_id=action.prompt_id,
            prompt_purpose=prompt_purpose,
            created_at=action.created_at,
            content_preview=content_preview,
            origin=getattr(action, 'origin', None)
        )

