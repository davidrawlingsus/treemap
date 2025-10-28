from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), default="intercom")  # Business context (intercom, survey, etc.)
    source_format = Column(String(50), default="intercom_mrt")  # Data structure format
    raw_data = Column(JSONB, nullable=False)  # Original uploaded data
    normalized_data = Column(JSONB)  # Transformed/normalized data for visualization
    is_normalized = Column(Boolean, default=False)  # Whether normalization has been applied
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, format={self.source_format})>"


