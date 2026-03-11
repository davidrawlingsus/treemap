from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class LeadgenVocRun(Base):
    __tablename__ = "leadgen_voc_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, unique=True, index=True)
    work_email = Column(String(255), nullable=False)
    company_domain = Column(String(255), nullable=False, index=True)
    company_url = Column(Text, nullable=False)
    company_name = Column(String(255), nullable=False)
    review_count = Column(Integer, nullable=False, default=0)
    coding_enabled = Column(Boolean, nullable=False, default=False)
    coding_status = Column(String(50), nullable=True)
    payload = Column(JSONB, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    converted_client_uuid = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    converted_client = relationship("Client", foreign_keys=[converted_client_uuid])
    rows = relationship("LeadgenVocRow", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LeadgenVocRun(id={self.id}, run_id={self.run_id}, company_domain={self.company_domain})>"


class LeadgenVocRow(Base):
    __tablename__ = "leadgen_voc_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("leadgen_voc_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    respondent_id = Column(String(50), nullable=False)
    created = Column(DateTime(timezone=True), nullable=True)
    last_modified = Column(DateTime(timezone=True), nullable=True)
    client_id = Column(String(50), nullable=True)
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
    question_type = Column(String(50), nullable=True, default="open_text")
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    run = relationship("LeadgenVocRun", back_populates="rows")

    def __repr__(self):
        return f"<LeadgenVocRow(id={self.id}, run_id={self.run_id}, respondent_id={self.respondent_id})>"
