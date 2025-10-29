from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class GrowthIdea(Base):
    __tablename__ = "growth_ideas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), nullable=False)
    dimension_ref_key = Column(String(100), nullable=False)  # e.g., "ref_1"
    dimension_name = Column(String(255), nullable=True)  # Human-readable name
    idea_text = Column(Text, nullable=False)  # The generated idea
    status = Column(String(20), default="pending")  # pending, accepted, rejected
    priority = Column(Integer, nullable=True)  # 1=high, 2=medium, 3=low
    context_data = Column(JSONB, nullable=True)  # Snapshot of data used to generate
    generation_prompt = Column(Text, nullable=True)  # The prompt sent to LLM
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    client = relationship("Client", back_populates="growth_ideas")
    data_source = relationship("DataSource", back_populates="growth_ideas")

    def __repr__(self):
        return f"<GrowthIdea(id={self.id}, client_id={self.client_id}, status={self.status})>"

