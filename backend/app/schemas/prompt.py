"""
Prompt engineering schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class PromptCreate(BaseModel):
    """Create a new prompt"""
    name: str = Field(..., description="Human-readable identifier for the prompt")
    version: int = Field(..., description="Version number for version control")
    prompt_text: str = Field(..., description="The actual system prompt text")
    prompt_purpose: str = Field(..., description="Purpose/type (e.g., 'summarize', 'headlines', 'ux-fixes')")
    status: str = Field(default="test", description="Status: 'live', 'test', or 'archived'")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model identifier")


class PromptUpdate(BaseModel):
    """Update an existing prompt"""
    name: Optional[str] = None
    version: Optional[int] = None
    prompt_text: Optional[str] = None
    prompt_purpose: Optional[str] = None
    status: Optional[str] = None
    llm_model: Optional[str] = None


class PromptResponse(BaseModel):
    """Response schema for a prompt"""
    id: UUID
    name: str
    version: int
    prompt_text: str
    prompt_purpose: str
    status: str
    llm_model: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

