from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class DimensionName(Base):
    """
    Stores custom human-readable names for survey questions/dimensions.
    Maps ref_key (e.g., 'ref_1') to a custom display name for each data source.
    """
    __tablename__ = "dimension_names"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id', ondelete='CASCADE'), nullable=False)
    ref_key = Column(String(100), nullable=False)  # e.g., "ref_1", "ref_2"
    custom_name = Column(String(255), nullable=False)  # e.g., "Customer Satisfaction", "Product Quality"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to data source
    data_source = relationship("DataSource", back_populates="dimension_names")

    # Unique constraint: one custom name per ref_key per data source
    __table_args__ = (
        UniqueConstraint('data_source_id', 'ref_key', name='uq_data_source_ref_key'),
    )

    def __repr__(self):
        return f"<DimensionName(ref_key={self.ref_key}, custom_name={self.custom_name})>"

