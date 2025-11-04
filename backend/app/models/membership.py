from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    role = Column(String(50), nullable=False, default='viewer')  # owner, admin, viewer
    status = Column(String(50), nullable=False, default='active')  # active, inactive, pending
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    membership_metadata = Column("metadata", JSONB, nullable=True)  # Column name is "metadata" in DB, but attribute is "membership_metadata"
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="memberships")
    client = relationship("Client", back_populates="memberships")
    inviter = relationship("User", foreign_keys=[invited_by], back_populates="invitations_sent")

    # Unique constraint: one membership per user-client pair
    __table_args__ = (
        UniqueConstraint('user_id', 'client_id', name='memberships_user_client_unique'),
    )

    def __repr__(self):
        return f"<Membership(user_id={self.user_id}, client_id={self.client_id}, role={self.role})>"

