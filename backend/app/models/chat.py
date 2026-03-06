from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class ChatVisitorSession(Base):
    __tablename__ = "chat_visitor_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_token = Column(String(128), nullable=False, unique=True, index=True)
    authenticated_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    session_metadata = Column("metadata", JSONB, nullable=True, default=dict)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[authenticated_user_id])
    conversations = relationship("ChatConversation", back_populates="visitor_session")


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_session_id = Column(UUID(as_uuid=True), ForeignKey("chat_visitor_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="open")
    source_url = Column(Text, nullable=True)
    source_path = Column(String(255), nullable=True)
    source_title = Column(String(255), nullable=True)
    referrer_url = Column(Text, nullable=True)
    conversation_metadata = Column("metadata", JSONB, nullable=True, default=dict)
    last_message_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    visitor_session = relationship("ChatVisitorSession", back_populates="conversations")
    user = relationship("User", foreign_keys=[user_id])
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    slack_thread = relationship(
        "ChatSlackThread",
        back_populates="conversation",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = Column(String(50), nullable=False)
    sender_label = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    slack_channel_id = Column(String(64), nullable=True)
    slack_ts = Column(String(64), nullable=True, index=True)
    client_message_id = Column(String(128), nullable=True)
    message_metadata = Column("metadata", JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    conversation = relationship("ChatConversation", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_conversation_created_at", "conversation_id", "created_at"),
    )


class ChatSlackThread(Base):
    __tablename__ = "chat_slack_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, unique=True)
    channel_id = Column(String(64), nullable=False, index=True)
    thread_ts = Column(String(64), nullable=False, unique=True, index=True)
    initial_message_ts = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    conversation = relationship("ChatConversation", back_populates="slack_thread")
