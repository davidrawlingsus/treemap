"""Ad Library media item (video or image) linked to an ad."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class AdLibraryMedia(Base):
    """Single media item (video or image) scraped from an Ad Library ad card."""
    __tablename__ = "ad_library_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_id = Column(UUID(as_uuid=True), ForeignKey('ad_library_ads.id', ondelete='CASCADE'), nullable=False)
    media_type = Column(String(20), nullable=False)  # image | video
    url = Column(Text, nullable=False)
    poster_url = Column(Text, nullable=True)  # video poster/thumbnail
    duration_seconds = Column(Integer, nullable=True)  # video length
    sort_order = Column(Integer, nullable=False, default=0)  # carousel order
    video_analysis_json = Column(JSONB, nullable=True)  # Gemini output for video ads
    image_analysis_json = Column(JSONB, nullable=True)  # Gemini output for image ads
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    ad = relationship("AdLibraryAd", back_populates="media_items")

    def __repr__(self):
        return f"<AdLibraryMedia(id={self.id}, ad_id={self.ad_id}, type={self.media_type})>"
