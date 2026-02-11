from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class AdLibraryAd(Base):
    """Single ad row from an Ad Library import (copy, metadata, media)."""
    __tablename__ = "ad_library_ads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_id = Column(UUID(as_uuid=True), ForeignKey('ad_library_imports.id', ondelete='CASCADE'), nullable=False)
    primary_text = Column(Text, nullable=False)
    headline = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    library_id = Column(String(100), nullable=True)
    started_running_on = Column(String(100), nullable=True)  # e.g. "Jan 15, 2024"
    # Extended: timeline, format, CTA, thumbnail
    ad_delivery_start_time = Column(String(100), nullable=True)
    ad_delivery_end_time = Column(String(100), nullable=True)
    ad_format = Column(String(50), nullable=True)  # video | image | carousel
    cta = Column(String(200), nullable=True)
    destination_url = Column(Text, nullable=True)
    media_thumbnail_url = Column(Text, nullable=True)
    # New: full scraped metadata
    status = Column(String(50), nullable=True)  # Active | Paused | Ended
    platforms = Column(JSONB, nullable=True)  # ["meta","instagram",...]
    ads_using_creative_count = Column(Integer, nullable=True)
    page_name = Column(String(255), nullable=True)
    page_url = Column(Text, nullable=True)
    page_profile_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    import_run = relationship("AdLibraryImport", back_populates="ads")
    media_items = relationship("AdLibraryMedia", back_populates="ad", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AdLibraryAd(id={self.id}, import_id={self.import_id})>"
