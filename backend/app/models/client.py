from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
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
    business_summary = Column(Text, nullable=True)
    client_url = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    header_color = Column(String(7), nullable=True)
    tone_of_voice = Column(Text, nullable=True)
    ad_library_only = Column(Boolean, default=False)  # Diagnosis-only brand (not in viz app)

    # Relationships
    founder = relationship("User", foreign_keys=[founder_user_id], back_populates="founded_clients")
    data_sources = relationship("DataSource", back_populates="client")
    memberships = relationship("Membership", back_populates="client")
    actions = relationship("Action", back_populates="client")
    authorized_domains = relationship(
        "AuthorizedDomain",
        secondary="authorized_domain_clients",
        back_populates="clients",
        overlaps="authorized_domain_links,client_links",
    )
    authorized_domain_links = relationship(
        "AuthorizedDomainClient",
        back_populates="client",
        cascade="all, delete-orphan",
        overlaps="authorized_domains,clients,client_links",
    )
    authorized_emails = relationship(
        "AuthorizedEmail",
        secondary="authorized_email_clients",
        back_populates="clients",
        overlaps="authorized_email_links,client_links",
    )
    authorized_email_links = relationship(
        "AuthorizedEmailClient",
        back_populates="client",
        cascade="all, delete-orphan",
        overlaps="authorized_emails,clients,client_links",
    )
    # Relationships for client-facing prompts (many-to-many with prompts)
    prompts = relationship(
        "Prompt",
        secondary="prompt_clients",
        back_populates="clients",
        overlaps="prompt_client_links"
    )
    prompt_links = relationship(
        "PromptClient",
        back_populates="client",
        cascade="all, delete-orphan",
        overlaps="prompts,clients"
    )

    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name}, slug={self.slug})>"

