"""
SavedEmail model for storing email ideas/templates.
Follows the pattern established by FacebookAd model.
"""
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class SavedEmail(Base):
    __tablename__ = "saved_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    action_id = Column(UUID(as_uuid=True), ForeignKey('actions.id', ondelete='SET NULL'), nullable=True)
    
    # Email type for filtering (post_purchase_onboarding, cart_abandonment, replenishment_reminder, browse_abandonment)
    email_type = Column(String(100), nullable=True)
    
    # Core email fields
    subject_line = Column(String(255), nullable=False)
    preview_text = Column(String(255), nullable=True)
    from_name = Column(String(100), nullable=True)
    headline = Column(String(255), nullable=True)
    body_text = Column(Text, nullable=False)
    discount_code = Column(String(50), nullable=True)
    social_proof = Column(Text, nullable=True)
    cta_text = Column(String(100), nullable=True)
    cta_url = Column(Text, nullable=True)
    
    # Sequence fields
    sequence_position = Column(Integer, nullable=True)
    send_delay_hours = Column(Integer, nullable=True)
    
    # Evidence and strategy
    voc_evidence = Column(JSONB, nullable=True, default=[])  # Array of VoC quotes
    strategic_intent = Column(Text, nullable=True)
    
    # Complete original JSON for future Klaviyo export (includes image_url when set)
    full_json = Column(JSONB, nullable=False)
    
    # Status workflow: draft -> ready -> exported
    status = Column(String(50), nullable=False, default='draft')
    
    # Klaviyo integration (future sprint)
    klaviyo_campaign_id = Column(String(100), nullable=True)
    
    # Timestamps and ownership
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    action = relationship("Action", foreign_keys=[action_id])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<SavedEmail(id={self.id}, subject_line={self.subject_line}, client_id={self.client_id})>"
