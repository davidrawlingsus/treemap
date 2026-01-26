from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class FacebookAd(Base):
    __tablename__ = "facebook_ads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    insight_id = Column(UUID(as_uuid=True), ForeignKey('insights.id', ondelete='SET NULL'), nullable=True)
    action_id = Column(UUID(as_uuid=True), ForeignKey('actions.id', ondelete='SET NULL'), nullable=True)
    primary_text = Column(Text, nullable=False)
    headline = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    call_to_action = Column(String(50), nullable=False)
    destination_url = Column(Text, nullable=True)
    image_hash = Column(Text, nullable=True)  # Image prompt from LLM
    voc_evidence = Column(JSONB, nullable=True, default=[])  # Array of VoC quotes
    full_json = Column(JSONB, nullable=False)  # Complete original JSON for FB API
    status = Column(String(50), nullable=False, default='draft')  # draft, ready, exported
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    insight = relationship("Insight", foreign_keys=[insight_id])
    action = relationship("Action", foreign_keys=[action_id])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<FacebookAd(id={self.id}, headline={self.headline}, client_id={self.client_id})>"
