from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False)
    prompt_type = Column(String(50), nullable=False, default='system')  # 'system' or 'helper'
    system_message = Column(Text, nullable=True)  # Required for system prompts, NULL for helper prompts
    prompt_message = Column(Text, nullable=True)  # Required for helper prompts, NULL for system prompts
    prompt_purpose = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default='test')  # live, test, archived
    llm_model = Column(String(100), nullable=False, default='gpt-4o-mini')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    actions = relationship("Action", back_populates="prompt", cascade="all, delete-orphan")
    # Relationships for helper prompts (system prompts can have multiple helper prompts)
    helper_prompts = relationship(
        "PromptHelperPrompt",
        foreign_keys="[PromptHelperPrompt.system_prompt_id]",
        back_populates="system_prompt",
        cascade="all, delete-orphan"
    )
    # Relationships for system prompts (helper prompts can be linked to multiple system prompts)
    system_prompts = relationship(
        "PromptHelperPrompt",
        foreign_keys="[PromptHelperPrompt.helper_prompt_id]",
        back_populates="helper_prompt",
        cascade="all, delete-orphan"
    )

    # Unique constraint: one prompt per name+version combination
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_prompt_name_version'),
    )

    def __repr__(self):
        return f"<Prompt(id={self.id}, name={self.name}, version={self.version}, type={self.prompt_type}, status={self.status})>"


class PromptHelperPrompt(Base):
    """Junction table linking system prompts to helper prompts"""
    __tablename__ = "prompt_helper_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_prompt_id = Column(UUID(as_uuid=True), ForeignKey('prompts.id', ondelete='CASCADE'), nullable=False)
    helper_prompt_id = Column(UUID(as_uuid=True), ForeignKey('prompts.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    system_prompt = relationship("Prompt", foreign_keys=[system_prompt_id], back_populates="helper_prompts")
    helper_prompt = relationship("Prompt", foreign_keys=[helper_prompt_id], back_populates="system_prompts")

    # Unique constraint: one link per system-helper pair
    __table_args__ = (
        UniqueConstraint('system_prompt_id', 'helper_prompt_id', name='uq_system_helper_prompt'),
    )

    def __repr__(self):
        return f"<PromptHelperPrompt(system_prompt_id={self.system_prompt_id}, helper_prompt_id={self.helper_prompt_id})>"

