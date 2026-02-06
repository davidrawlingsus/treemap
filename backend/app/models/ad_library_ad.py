from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class AdLibraryAd(Base):
    """Single ad copy row from an Ad Library import (for VOC comparison)."""
    __tablename__ = "ad_library_ads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_id = Column(UUID(as_uuid=True), ForeignKey('ad_library_imports.id', ondelete='CASCADE'), nullable=False)
    primary_text = Column(Text, nullable=False)
    headline = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    library_id = Column(String(100), nullable=True)
    started_running_on = Column(String(100), nullable=True)  # e.g. "Jan 15, 2024"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    import_run = relationship("AdLibraryImport", back_populates="ads")

    def __repr__(self):
        return f"<AdLibraryAd(id={self.id}, import_id={self.import_id})>"
