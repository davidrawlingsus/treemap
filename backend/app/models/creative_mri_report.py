from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class CreativeMRIReport(Base):
    """Stored Creative MRI report runs. Status: pending, running, complete, failed."""
    __tablename__ = "creative_mri_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    ad_library_import_id = Column(
        UUID(as_uuid=True),
        ForeignKey('ad_library_imports.id', ondelete='SET NULL'),
        nullable=True,
    )
    status = Column(String(20), nullable=False)  # pending, running, complete, failed
    report_json = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    progress_current = Column(Integer, nullable=True)
    progress_total = Column(Integer, nullable=True)
    progress_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    ad_library_import = relationship("AdLibraryImport", foreign_keys=[ad_library_import_id])

    def __repr__(self):
        return f"<CreativeMRIReport(id={self.id}, status={self.status}, client_id={self.client_id})>"
