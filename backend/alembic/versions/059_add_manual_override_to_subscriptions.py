"""Add is_manual_override to subscriptions

Revision ID: 059
Revises: 058
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa


revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "subscriptions",
        sa.Column("is_manual_override", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("subscriptions", "is_manual_override")
