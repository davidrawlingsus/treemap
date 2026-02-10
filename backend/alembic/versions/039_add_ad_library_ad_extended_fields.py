"""Add extended fields to ad_library_ads: timeline, format, CTA, thumbnail

Revision ID: 039
Revises: 038
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa

revision = '039'
down_revision = '038'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ad_library_ads', sa.Column('ad_delivery_start_time', sa.String(100), nullable=True))
    op.add_column('ad_library_ads', sa.Column('ad_delivery_end_time', sa.String(100), nullable=True))
    op.add_column('ad_library_ads', sa.Column('ad_format', sa.String(50), nullable=True))
    op.add_column('ad_library_ads', sa.Column('cta', sa.String(200), nullable=True))
    op.add_column('ad_library_ads', sa.Column('destination_url', sa.Text(), nullable=True))
    op.add_column('ad_library_ads', sa.Column('media_thumbnail_url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('ad_library_ads', 'media_thumbnail_url')
    op.drop_column('ad_library_ads', 'destination_url')
    op.drop_column('ad_library_ads', 'cta')
    op.drop_column('ad_library_ads', 'ad_format')
    op.drop_column('ad_library_ads', 'ad_delivery_end_time')
    op.drop_column('ad_library_ads', 'ad_delivery_start_time')
