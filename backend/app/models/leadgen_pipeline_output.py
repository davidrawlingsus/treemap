from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class LeadgenPipelineOutput(Base):
    __tablename__ = "leadgen_pipeline_outputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String(64),
        ForeignKey("leadgen_voc_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_type = Column(String(50), nullable=False)  # context, extract, taxonomy, validate, generate
    step_order = Column(Integer, nullable=False)
    output = Column(JSONB, nullable=False)
    elapsed_seconds = Column(Float, nullable=True)
    prompt_version_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    run = relationship("LeadgenVocRun", foreign_keys=[run_id])
    prompt_version = relationship("Prompt", foreign_keys=[prompt_version_id])

    def __repr__(self):
        return f"<LeadgenPipelineOutput(id={self.id}, run_id={self.run_id}, step_type={self.step_type})>"
