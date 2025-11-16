from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class DimensionSummary(Base):
    """
    Stores AI-generated summaries for dimensions.
    One summary per unique combination of client/data_source/dimension.
    Cached to avoid repeated API calls.
    """
    __tablename__ = "dimension_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_uuid = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    data_source = Column(String(255), nullable=False)
    dimension_ref = Column(String(50), nullable=False)
    dimension_name = Column(Text, nullable=True)
    
    # AI-generated content (parsed from OpenAI response)
    summary_text = Column(Text, nullable=False)  # 2-paragraph summary
    key_insights = Column(JSONB, nullable=True)  # Array of bullet points
    category_snapshot = Column(JSONB, nullable=True)  # Category -> insight mapping
    patterns = Column(Text, nullable=True)  # Sentiment/behavioral patterns
    
    # Metadata about the generation
    sample_size = Column(Integer, nullable=False)  # Number of responses sampled
    total_responses = Column(Integer, nullable=False)  # Total available responses
    model_used = Column(String(50), default="gpt-4o-mini")  # OpenAI model version
    tokens_used = Column(Integer, nullable=True)  # For cost tracking
    topic_distribution = Column(JSONB, nullable=True)  # Full dataset breakdown
    generation_duration_ms = Column(Integer, nullable=True)  # Performance tracking
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    client = relationship("Client", foreign_keys=[client_uuid])

    # Unique constraint: one summary per dimension
    __table_args__ = (
        UniqueConstraint('client_uuid', 'data_source', 'dimension_ref', name='uq_client_source_dimension_summary'),
    )

    def __repr__(self):
        return f"<DimensionSummary(dimension_ref={self.dimension_ref}, client_uuid={self.client_uuid})>"

