"""
Founder-managed default copy for custom deal pages.
Single-row settings table — only one set of defaults exists.
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class DealPageDefaults(Base):
    __tablename__ = "deal_page_defaults"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pause_cancel_text = Column(Text, nullable=True)
    no_charge_text = Column(Text, nullable=True)
    success_message = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
