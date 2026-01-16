from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class AuthorizedEmail(Base):
    __tablename__ = "authorized_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    clients = relationship(
        "Client",
        secondary="authorized_email_clients",
        back_populates="authorized_emails",
        overlaps="authorized_email_links,client_links",
    )
    client_links = relationship(
        "AuthorizedEmailClient",
        back_populates="email",
        cascade="all, delete-orphan",
        overlaps="authorized_emails,clients",
    )

    def __repr__(self):
        return f"<AuthorizedEmail(email={self.email})>"


class AuthorizedEmailClient(Base):
    __tablename__ = "authorized_email_clients"

    email_id = Column(
        UUID(as_uuid=True),
        ForeignKey("authorized_emails.id", ondelete="CASCADE"),
        primary_key=True,
    )
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    email = relationship(
        "AuthorizedEmail",
        back_populates="client_links",
        overlaps="authorized_emails,clients,authorized_email_links",
    )
    client = relationship(
        "Client",
        back_populates="authorized_email_links",
        overlaps="authorized_emails,client_links,clients",
    )

    __table_args__ = (
        UniqueConstraint("email_id", "client_id", name="authorized_email_client_key"),
    )

