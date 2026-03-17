"""add order_context_json to shopify_survey_responses

Revision ID: 065
Revises: 064
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "shopify_survey_responses",
        sa.Column("order_context_json", JSONB, nullable=True),
    )


def downgrade():
    op.drop_column("shopify_survey_responses", "order_context_json")
