"""Add ad_library_media table and extended fields to ad_library_ads

Revision ID: 043
Revises: 042
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '043'
down_revision = '042'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = {c['name'] for c in inspector.get_columns('ad_library_ads')}

    # Add new columns to ad_library_ads (skip if already exist)
    if 'status' not in existing_columns:
        op.add_column('ad_library_ads', sa.Column('status', sa.String(50), nullable=True))
    if 'platforms' not in existing_columns:
        op.add_column('ad_library_ads', sa.Column('platforms', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if 'ads_using_creative_count' not in existing_columns:
        op.add_column('ad_library_ads', sa.Column('ads_using_creative_count', sa.Integer(), nullable=True))
    if 'page_name' not in existing_columns:
        op.add_column('ad_library_ads', sa.Column('page_name', sa.String(255), nullable=True))
    if 'page_url' not in existing_columns:
        op.add_column('ad_library_ads', sa.Column('page_url', sa.Text(), nullable=True))
    if 'page_profile_image_url' not in existing_columns:
        op.add_column('ad_library_ads', sa.Column('page_profile_image_url', sa.Text(), nullable=True))

    # Create ad_library_media table if not exists
    existing_tables = inspector.get_table_names()
    if 'ad_library_media' not in existing_tables:
        op.create_table(
            'ad_library_media',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('ad_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ad_library_ads.id', ondelete='CASCADE'), nullable=False),
            sa.Column('media_type', sa.String(20), nullable=False),
            sa.Column('url', sa.Text(), nullable=False),
            sa.Column('poster_url', sa.Text(), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_ad_library_media_ad_id', 'ad_library_media', ['ad_id'])


def downgrade():
    op.drop_index('ix_ad_library_media_ad_id', table_name='ad_library_media')
    op.drop_table('ad_library_media')
    op.drop_column('ad_library_ads', 'page_profile_image_url')
    op.drop_column('ad_library_ads', 'page_url')
    op.drop_column('ad_library_ads', 'page_name')
    op.drop_column('ad_library_ads', 'ads_using_creative_count')
    op.drop_column('ad_library_ads', 'platforms')
    op.drop_column('ad_library_ads', 'status')
