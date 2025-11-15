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


class AuthorizedDomain(Base):
    __tablename__ = "authorized_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), nullable=False, unique=True)
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
        secondary="authorized_domain_clients",
        back_populates="authorized_domains",
        overlaps="authorized_domain_links,client_links",
    )
    client_links = relationship(
        "AuthorizedDomainClient",
        back_populates="domain",
        cascade="all, delete-orphan",
        overlaps="authorized_domains,clients",
    )

    def __repr__(self):
        return f"<AuthorizedDomain(domain={self.domain})>"


class AuthorizedDomainClient(Base):
    __tablename__ = "authorized_domain_clients"

    domain_id = Column(
        UUID(as_uuid=True),
        ForeignKey("authorized_domains.id", ondelete="CASCADE"),
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

    domain = relationship(
        "AuthorizedDomain",
        back_populates="client_links",
        overlaps="authorized_domains,clients,authorized_domain_links",
    )
    client = relationship(
        "Client",
        back_populates="authorized_domain_links",
        overlaps="authorized_domains,client_links,clients",
    )

    __table_args__ = (
        UniqueConstraint("domain_id", "client_id", name="authorized_domain_client_key"),
    )


