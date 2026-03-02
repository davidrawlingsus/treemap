"""Add adset fields to ad_image_performance

Revision ID: 057
Revises: 056
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ad_image_performance", sa.Column("meta_adset_id", sa.String(length=64), nullable=True))
    op.add_column("ad_image_performance", sa.Column("meta_adset_name", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("ad_image_performance", "meta_adset_name")
    op.drop_column("ad_image_performance", "meta_adset_id")
