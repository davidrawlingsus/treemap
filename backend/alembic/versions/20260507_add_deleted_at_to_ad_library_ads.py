"""Add deleted_at column to ad_library_ads (soft delete)

Revision ID: d5f7a9b2c4e6
Revises: c4e6f8a0b2d4
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


revision = "d5f7a9b2c4e6"
down_revision = "c4e6f8a0b2d4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ad_library_ads",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ad_library_ads_deleted_at",
        "ad_library_ads",
        ["deleted_at"],
    )


def downgrade():
    op.drop_index("ix_ad_library_ads_deleted_at", table_name="ad_library_ads")
    op.drop_column("ad_library_ads", "deleted_at")
