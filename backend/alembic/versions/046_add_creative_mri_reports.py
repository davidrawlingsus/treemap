"""Add creative_mri_reports table for stored reports

Revision ID: 046
Revises: 045
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '046'
down_revision = '045'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'creative_mri_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ad_library_import_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ad_library_imports.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('report_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_creative_mri_reports_client_id', 'creative_mri_reports', ['client_id'])
    op.create_index('ix_creative_mri_reports_status', 'creative_mri_reports', ['status'])
    op.create_index('ix_creative_mri_reports_created_at', 'creative_mri_reports', ['created_at'])


def downgrade():
    op.drop_index('ix_creative_mri_reports_created_at', table_name='creative_mri_reports')
    op.drop_index('ix_creative_mri_reports_status', table_name='creative_mri_reports')
    op.drop_index('ix_creative_mri_reports_client_id', table_name='creative_mri_reports')
    op.drop_table('creative_mri_reports')
