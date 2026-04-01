from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class LeadEmail(Base):
    __tablename__ = "lead_email_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(String(64), ForeignKey("leadgen_voc_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    email_address = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    preview_text = Column(String(255), nullable=True)
    template_data = Column(JSONB, nullable=True)
    html_body = Column(Text, nullable=True)
    text_body = Column(Text, nullable=True)
    sequence_number = Column(Integer, nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    resend_email_id = Column(String(100), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    run = relationship("LeadgenVocRun", foreign_keys=[run_id], primaryjoin="LeadEmail.run_id == LeadgenVocRun.run_id")

    def __repr__(self):
        return f"<LeadEmail(id={self.id}, run_id={self.run_id}, seq={self.sequence_number}, status={self.status})>"
