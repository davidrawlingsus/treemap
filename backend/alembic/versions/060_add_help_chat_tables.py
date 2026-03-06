"""Add help chat tables

Revision ID: 060
Revises: 059
Create Date: 2026-03-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_visitor_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visitor_token", sa.String(length=128), nullable=False),
        sa.Column("authenticated_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["authenticated_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("visitor_token"),
    )
    op.create_index("ix_chat_visitor_sessions_visitor_token", "chat_visitor_sessions", ["visitor_token"], unique=True)

    op.create_table(
        "chat_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visitor_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_path", sa.String(length=255), nullable=True),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("referrer_url", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["visitor_session_id"], ["chat_visitor_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_conversations_last_message_at", "chat_conversations", ["last_message_at"], unique=False)
    op.create_index("ix_chat_conversations_user_id", "chat_conversations", ["user_id"], unique=False)
    op.create_index("ix_chat_conversations_visitor_session_id", "chat_conversations", ["visitor_session_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_type", sa.String(length=50), nullable=False),
        sa.Column("sender_label", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("slack_channel_id", sa.String(length=64), nullable=True),
        sa.Column("slack_ts", sa.String(length=64), nullable=True),
        sa.Column("client_message_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_conversation_created_at", "chat_messages", ["conversation_id", "created_at"], unique=False)
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"], unique=False)
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"], unique=False)
    op.create_index("ix_chat_messages_slack_ts", "chat_messages", ["slack_ts"], unique=False)

    op.create_table(
        "chat_slack_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("thread_ts", sa.String(length=64), nullable=False),
        sa.Column("initial_message_ts", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id"),
        sa.UniqueConstraint("thread_ts"),
    )
    op.create_index("ix_chat_slack_threads_channel_id", "chat_slack_threads", ["channel_id"], unique=False)
    op.create_index("ix_chat_slack_threads_thread_ts", "chat_slack_threads", ["thread_ts"], unique=True)


def downgrade():
    op.drop_index("ix_chat_slack_threads_thread_ts", table_name="chat_slack_threads")
    op.drop_index("ix_chat_slack_threads_channel_id", table_name="chat_slack_threads")
    op.drop_table("chat_slack_threads")

    op.drop_index("ix_chat_messages_slack_ts", table_name="chat_messages")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_created_at", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_conversations_visitor_session_id", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_user_id", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_last_message_at", table_name="chat_conversations")
    op.drop_table("chat_conversations")

    op.drop_index("ix_chat_visitor_sessions_visitor_token", table_name="chat_visitor_sessions")
    op.drop_table("chat_visitor_sessions")
