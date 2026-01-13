from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Action(Base):
    __tablename__ = "actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey('prompts.id', ondelete='CASCADE'), nullable=False)
    prompt_text_sent = Column(Text, nullable=False)
    actions = Column(JSONB, nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    insight_ids = Column(JSONB, nullable=False, default=[])
    origin = Column(JSONB, nullable=True)  # Origin metadata (same structure as insight origins)
    voc_json = Column(JSONB, nullable=True)  # Source VoC JSON object used when executing the prompt
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    prompt = relationship("Prompt", back_populates="actions")
    client = relationship("Client", back_populates="actions")

    def __repr__(self):
        return f"<Action(id={self.id}, prompt_id={self.prompt_id}, client_id={self.client_id})>"

