"""add ad_images table

Revision ID: 034
Revises: 032
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '034'
down_revision = '032'
branch_labels = None
depends_on = None


def upgrade():
    # Create ad_images table
    op.create_table(
        'ad_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes
    op.create_index('ix_ad_images_client_id', 'ad_images', ['client_id'])
    op.create_index('ix_ad_images_uploaded_at', 'ad_images', ['uploaded_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_ad_images_uploaded_at', table_name='ad_images')
    op.drop_index('ix_ad_images_client_id', table_name='ad_images')
    
    # Drop table
    op.drop_table('ad_images')
