"""
Meta OAuth Token model for storing Facebook/Meta API credentials per client.
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class MetaOAuthToken(Base):
    """
    Stores Meta/Facebook OAuth tokens per client.
    Each client can have one active Meta connection.
    """
    __tablename__ = "meta_oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # OAuth token data
    access_token = Column(Text, nullable=False)  # Long-lived access token
    token_type = Column(String(50), nullable=False, default='bearer')
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Token expiration time
    
    # Meta user info
    meta_user_id = Column(String(100), nullable=True)  # Meta user ID who authorized
    meta_user_name = Column(String(255), nullable=True)  # Meta user name
    
    # Default ad account for this client
    default_ad_account_id = Column(String(100), nullable=True)  # e.g., "act_123456789"
    default_ad_account_name = Column(String(255), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<MetaOAuthToken(id={self.id}, client_id={self.client_id}, meta_user_id={self.meta_user_id})>"

    def is_expired(self):
        """Check if the token has expired."""
        if self.expires_at is None:
            return False
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) >= self.expires_at
