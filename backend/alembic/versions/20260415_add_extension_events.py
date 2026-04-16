"""Add extension_events table for analytics

Revision ID: c4e6f8a0b2d4
Revises: b3d5e7f9a1c3
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "c4e6f8a0b2d4"
down_revision = "b3d5e7f9a1c3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "extension_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event", sa.String(50), nullable=False, index=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("advertiser_domain", sa.String(255), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade():
    op.drop_table("extension_events")
