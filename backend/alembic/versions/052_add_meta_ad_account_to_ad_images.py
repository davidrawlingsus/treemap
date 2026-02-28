"""add meta_ad_account_id and meta_thumbnail_url to ad_images

Revision ID: 052
Revises: 051
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa


revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ad_images", sa.Column("meta_ad_account_id", sa.String(50), nullable=True))
    op.add_column("ad_images", sa.Column("meta_thumbnail_url", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ad_images", "meta_thumbnail_url")
    op.drop_column("ad_images", "meta_ad_account_id")
