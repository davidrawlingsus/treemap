"""Add import_jobs table and metadata fields to ad_images

Revision ID: 037
Revises: 036
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '037'
down_revision = '036'
branch_labels = None
depends_on = None


def upgrade():
    # Create import_jobs table first (ad_images has FK to it)
    op.create_table(
        'import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('total_found', sa.Integer(), default=0),
        sa.Column('total_imported', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create index on client_id and status for efficient queries
    op.create_index('ix_import_jobs_client_id', 'import_jobs', ['client_id'])
    op.create_index('ix_import_jobs_status', 'import_jobs', ['status'])
    
    # Add new columns to ad_images
    op.add_column('ad_images', sa.Column('started_running_on', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ad_images', sa.Column('library_id', sa.String(100), nullable=True))
    op.add_column('ad_images', sa.Column('source_url', sa.Text(), nullable=True))
    op.add_column('ad_images', sa.Column('import_job_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint for import_job_id
    op.create_foreign_key(
        'fk_ad_images_import_job_id',
        'ad_images', 'import_jobs',
        ['import_job_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index on import_job_id for efficient queries
    op.create_index('ix_ad_images_import_job_id', 'ad_images', ['import_job_id'])


def downgrade():
    # Remove foreign key and index first
    op.drop_constraint('fk_ad_images_import_job_id', 'ad_images', type_='foreignkey')
    op.drop_index('ix_ad_images_import_job_id', table_name='ad_images')
    
    # Remove columns from ad_images
    op.drop_column('ad_images', 'import_job_id')
    op.drop_column('ad_images', 'source_url')
    op.drop_column('ad_images', 'library_id')
    op.drop_column('ad_images', 'started_running_on')
    
    # Drop indexes and table
    op.drop_index('ix_import_jobs_status', table_name='import_jobs')
    op.drop_index('ix_import_jobs_client_id', table_name='import_jobs')
    op.drop_table('import_jobs')
