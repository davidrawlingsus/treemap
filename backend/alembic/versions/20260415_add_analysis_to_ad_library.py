"""Add analysis columns to ad_library_ads and ad_library_imports

Revision ID: b3d5e7f9a1c3
Revises: e4a7b2c1d3f5
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "b3d5e7f9a1c3"
down_revision = "e4a7b2c1d3f5"
branch_labels = None
depends_on = None


def upgrade():
    # Per-ad critique data
    op.add_column("ad_library_ads", sa.Column("analysis_json", JSONB, nullable=True))
    op.add_column("ad_library_ads", sa.Column("analysis_text", sa.Text, nullable=True))

    # Import-level summary data
    op.add_column("ad_library_imports", sa.Column("synthesis_text", sa.Text, nullable=True))
    op.add_column("ad_library_imports", sa.Column("signal_text", sa.Text, nullable=True))
    op.add_column("ad_library_imports", sa.Column("ad_copy_score", sa.Integer, nullable=True))
    op.add_column("ad_library_imports", sa.Column("signal_score", sa.Integer, nullable=True))
    op.add_column("ad_library_imports", sa.Column("opportunity_score", sa.Float, nullable=True))


def downgrade():
    op.drop_column("ad_library_imports", "opportunity_score")
    op.drop_column("ad_library_imports", "signal_score")
    op.drop_column("ad_library_imports", "ad_copy_score")
    op.drop_column("ad_library_imports", "signal_text")
    op.drop_column("ad_library_imports", "synthesis_text")
    op.drop_column("ad_library_ads", "analysis_text")
    op.drop_column("ad_library_ads", "analysis_json")
