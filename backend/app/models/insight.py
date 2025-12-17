from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Insight(Base):
    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)  # e.g., "improvement", "feature", "bug", etc.
    application = Column(Text, nullable=True)  # Where/how to apply this insight
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)  # Formatted notes (HTML from WYSIWYG editor)
    origins = Column(JSONB, nullable=False, default=[])  # Array of origin objects
    meta_data = Column('metadata', JSONB, nullable=True, default={})  # For future extensibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Insight(id={self.id}, name={self.name}, client_id={self.client_id})>"


