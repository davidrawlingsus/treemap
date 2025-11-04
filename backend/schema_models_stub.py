# Auto-generated SQLAlchemy model stubs based on Railway schema
# TODO: Review and adjust types, relationships, and constraints

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, Numeric, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Clients(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    is_active = Column(Boolean)
    settings = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime)
    founder_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # TODO: Add relationships based on foreign keys
    # relationship to Users via founder_user_id


class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    is_founder = Column(Boolean, nullable=False)
    is_active = Column(Boolean, nullable=False)
    email_verified_at = Column(DateTime)
    last_login_at = Column(DateTime)
    metadata = Column(JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now())


class Memberships(Base):
    __tablename__ = "memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    role = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    invited_at = Column(DateTime)
    joined_at = Column(DateTime)
    metadata = Column(JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    # TODO: Add relationships based on foreign keys
    # relationship to Clients via client_id
    # relationship to Users via invited_by
    # relationship to Users via user_id


class ProcessVoc(Base):
    __tablename__ = "process_voc"

    id = Column(Integer, primary_key=True, nullable=False)
    respondent_id = Column(String(50), nullable=False)
    created = Column(DateTime)
    last_modified = Column(DateTime)
    client_id = Column(String(50))
    client_name = Column(String(255))
    project_id = Column(String(50))
    project_name = Column(String(255))
    total_rows = Column(Integer)
    data_source = Column(String(255))
    region = Column(String(50))
    response_type = Column(String(50))
    start_date = Column(DateTime)
    submit_date = Column(DateTime)
    user_type = Column(String(50))
    dimension_ref = Column(String(50), nullable=False)
    dimension_name = Column(Text)
    value = Column(Text)
    overall_sentiment = Column(String(50))
    topics = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())
    client_uuid = Column(UUID(as_uuid=True), ForeignKey('clients.id'))

    # TODO: Add relationships based on foreign keys
    # relationship to Clients via client_uuid

