from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    settings = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    founder_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    founder = relationship("User", foreign_keys=[founder_user_id], back_populates="founded_clients")
    data_sources = relationship("DataSource", back_populates="client")
    memberships = relationship("Membership", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name}, slug={self.slug})>"

