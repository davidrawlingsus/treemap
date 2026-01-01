from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False)
    prompt_text = Column(Text, nullable=False)
    prompt_purpose = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default='test')  # live, test, archived
    llm_model = Column(String(100), nullable=False, default='gpt-4o-mini')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    actions = relationship("Action", back_populates="prompt", cascade="all, delete-orphan")

    # Unique constraint: one prompt per name+version combination
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_prompt_name_version'),
    )

    def __repr__(self):
        return f"<Prompt(id={self.id}, name={self.name}, version={self.version}, status={self.status})>"

