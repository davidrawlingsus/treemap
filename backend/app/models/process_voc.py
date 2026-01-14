from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ProcessVoc(Base):
    __tablename__ = "process_voc"

    id = Column(Integer, primary_key=True, autoincrement=True)
    respondent_id = Column(String(50), nullable=False)
    created = Column(DateTime(timezone=True), nullable=True)
    last_modified = Column(DateTime(timezone=True), nullable=True)
    client_id = Column(String(50), nullable=True)  # Legacy client ID
    client_name = Column(String(255), nullable=True)
    project_id = Column(String(50), nullable=True)
    project_name = Column(String(255), nullable=True)
    total_rows = Column(Integer, nullable=True)
    data_source = Column(String(255), nullable=True)
    dimension_ref = Column(String(50), nullable=False)
    dimension_name = Column(Text, nullable=True)
    value = Column(Text, nullable=True)
    overall_sentiment = Column(String(50), nullable=True)
    topics = Column(JSONB, nullable=True)
    survey_metadata = Column(JSONB, nullable=True)
    question_text = Column(Text, nullable=True)
    question_type = Column(String(50), nullable=True, default='open_text')
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    client_uuid = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=True)
    is_favourite = Column(Boolean, nullable=True, default=False)
    processed = Column(Boolean, nullable=False, default=False)

    # Relationship to client
    client = relationship("Client", foreign_keys=[client_uuid])

    def __repr__(self):
        return f"<ProcessVoc(id={self.id}, respondent_id={self.respondent_id}, dimension_ref={self.dimension_ref})>"

