"""add meta_created_time to ad_images (Meta asset library date added)

Revision ID: 053
Revises: 052
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ad_images",
        sa.Column("meta_created_time", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("ad_images", "meta_created_time")
