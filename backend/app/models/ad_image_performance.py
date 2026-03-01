from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class AdImagePerformance(Base):
    __tablename__ = "ad_image_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_image_id = Column(UUID(as_uuid=True), ForeignKey("ad_images.id", ondelete="CASCADE"), nullable=False, unique=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    # Meta lineage
    meta_ad_account_id = Column(String(50), nullable=True)
    meta_ad_id = Column(String(64), nullable=True)
    meta_creative_id = Column(String(64), nullable=True)
    media_key = Column(String(128), nullable=True)  # image_hash or video_id
    media_type = Column(String(16), nullable=True)  # image or video

    # Creative copy
    ad_primary_text = Column(Text, nullable=True)
    ad_headline = Column(Text, nullable=True)
    ad_description = Column(Text, nullable=True)
    ad_call_to_action = Column(String(64), nullable=True)
    destination_url = Column(Text, nullable=True)
    started_running_on = Column(DateTime(timezone=True), nullable=True)

    # Performance metrics (lifetime)
    revenue = Column(Numeric(14, 2), nullable=True)
    spend = Column(Numeric(14, 2), nullable=True)
    impressions = Column(Integer, nullable=True)
    clicks = Column(Integer, nullable=True)
    purchases = Column(Integer, nullable=True)
    ctr = Column(Numeric(8, 4), nullable=True)
    roas = Column(Numeric(10, 4), nullable=True)

    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    ad_image = relationship("AdImage", back_populates="performance")
    client = relationship("Client", foreign_keys=[client_id])

    def __repr__(self):
        return f"<AdImagePerformance(ad_image_id={self.ad_image_id}, revenue={self.revenue}, roas={self.roas})>"
