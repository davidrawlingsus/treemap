from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class AdImage(Base):
    __tablename__ = "ad_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    url = Column(Text, nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Meta Ads Library metadata
    started_running_on = Column(DateTime(timezone=True), nullable=True)
    library_id = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)  # Original Meta Ads Library URL
    import_job_id = Column(UUID(as_uuid=True), ForeignKey('import_jobs.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    uploader = relationship("User", foreign_keys=[uploaded_by])
    import_job = relationship("ImportJob", back_populates="images")

    def __repr__(self):
        return f"<AdImage(id={self.id}, filename={self.filename}, client_id={self.client_id})>"
