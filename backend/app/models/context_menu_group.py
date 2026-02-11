from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class ContextMenuGroup(Base):
    """Top-level context menu groups for organizing prompts in the right-click menu"""
    __tablename__ = "context_menu_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Prompts that belong to this group
    prompts = relationship("Prompt", back_populates="context_menu_group")

    def __repr__(self):
        return f"<ContextMenuGroup(id={self.id}, label={self.label})>"
