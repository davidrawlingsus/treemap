from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class ImportJob(Base):
    """Tracks background import jobs from Meta Ads Library."""
    __tablename__ = "import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    source_url = Column(Text, nullable=False)  # Meta Ads Library URL
    
    # Job status: pending, running, complete, failed
    status = Column(String(20), default='pending', nullable=False)
    
    # Progress tracking
    total_found = Column(Integer, default=0)
    total_imported = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    user = relationship("User", foreign_keys=[user_id])
    images = relationship("AdImage", back_populates="import_job")

    def __repr__(self):
        return f"<ImportJob(id={self.id}, status={self.status}, client_id={self.client_id})>"
