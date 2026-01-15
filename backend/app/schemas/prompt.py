"""
Prompt engineering schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class PromptCreate(BaseModel):
    """Create a new prompt"""
    name: str = Field(..., description="Human-readable identifier for the prompt")
    version: int = Field(..., description="Version number for version control")
    prompt_type: str = Field(default="system", description="Type of prompt: 'system' or 'helper'")
    system_message: Optional[str] = Field(None, description="The actual system prompt text (required for system prompts)")
    prompt_message: Optional[str] = Field(None, description="The prompt message text (required for helper prompts)")
    prompt_purpose: str = Field(..., description="Purpose/type (e.g., 'summarize', 'headlines', 'ux-fixes')")
    status: str = Field(default="test", description="Status: 'live', 'test', or 'archived'")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model identifier")


class PromptUpdate(BaseModel):
    """Update an existing prompt"""
    name: Optional[str] = None
    version: Optional[int] = None
    prompt_type: Optional[str] = None
    system_message: Optional[str] = None
    prompt_message: Optional[str] = None
    prompt_purpose: Optional[str] = None
    status: Optional[str] = None
    llm_model: Optional[str] = None


class PromptResponse(BaseModel):
    """Response schema for a prompt"""
    id: UUID
    name: str
    version: int
    prompt_type: str
    system_message: Optional[str] = None
    prompt_message: Optional[str] = None
    prompt_purpose: str
    status: str
    llm_model: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PromptMenuItem(BaseModel):
    """Minimal prompt info for menu display (client-facing)"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ClientPromptExecuteRequest(BaseModel):
    """Request schema for executing a prompt from client interface"""
    voc_data: dict = Field(..., description="Voice of customer JSON data from category/topic")
    origin: Optional[Dict[str, Any]] = Field(None, description="Origin metadata (same structure as insight origins)")


class PromptHelperPromptResponse(BaseModel):
    """Response schema for a prompt helper prompt link"""
    id: UUID
    system_prompt_id: UUID
    helper_prompt_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

