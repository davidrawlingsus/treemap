from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class AdLibraryImport(Base):
    """One import run from Meta Ads Library (copy only) for a client."""
    __tablename__ = "ad_library_imports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    source_url = Column(Text, nullable=False)
    imported_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    ads = relationship("AdLibraryAd", back_populates="import_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AdLibraryImport(id={self.id}, client_id={self.client_id})>"
