from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    is_founder = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    user_metadata = Column("metadata", JSONB, nullable=True)  # Column name is "metadata" in DB, but attribute is "user_metadata"
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    # Clients where this user is the founder
    founded_clients = relationship("Client", foreign_keys="Client.founder_user_id", back_populates="founder")
    # Memberships (user's access to clients) - specify foreign_keys to avoid ambiguity
    memberships = relationship("Membership", foreign_keys="Membership.user_id", back_populates="user")
    # Invitations sent by this user
    invitations_sent = relationship("Membership", foreign_keys="Membership.invited_by", back_populates="inviter")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_founder={self.is_founder})>"

