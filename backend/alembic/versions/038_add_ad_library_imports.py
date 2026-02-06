"""Add ad_library_imports and ad_library_ads tables for VOC comparison

Revision ID: 038
Revises: 037
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '038'
down_revision = '037'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ad_library_imports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_ad_library_imports_client_id', 'ad_library_imports', ['client_id'])

    op.create_table(
        'ad_library_ads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('import_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ad_library_imports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('primary_text', sa.Text(), nullable=False),
        sa.Column('headline', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('library_id', sa.String(100), nullable=True),
        sa.Column('started_running_on', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_ad_library_ads_import_id', 'ad_library_ads', ['import_id'])


def downgrade():
    op.drop_index('ix_ad_library_ads_import_id', table_name='ad_library_ads')
    op.drop_table('ad_library_ads')
    op.drop_index('ix_ad_library_imports_client_id', table_name='ad_library_imports')
    op.drop_table('ad_library_imports')
