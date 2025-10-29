from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=True)  # Nullable for backward compatibility
    source_name = Column(String(255), nullable=True)  # e.g., "Success Page Survey", "Trustpilot"
    source_type = Column(String(50), default="intercom")  # Business context (intercom, survey, etc.)
    source_format = Column(String(50), default="intercom_mrt")  # Data structure format
    raw_data = Column(JSONB, nullable=False)  # Original uploaded data
    normalized_data = Column(JSONB)  # Transformed/normalized data for visualization
    is_normalized = Column(Boolean, default=False)  # Whether normalization has been applied
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to client
    client = relationship("Client", back_populates="data_sources")
    
    # Relationship to dimension names
    dimension_names = relationship("DimensionName", back_populates="data_source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, format={self.source_format})>"


