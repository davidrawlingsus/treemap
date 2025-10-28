"""add multi-tenant support

Revision ID: 001
Revises: 
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create clients table
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    
    # Add new columns to data_sources table (if it exists)
    # These are nullable to handle backward compatibility
    op.add_column('data_sources', sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('data_sources', sa.Column('source_name', sa.String(length=255), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_data_sources_client_id_clients',
        'data_sources', 'clients',
        ['client_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for better query performance
    op.create_index('ix_data_sources_client_id', 'data_sources', ['client_id'])
    op.create_index('ix_data_sources_source_name', 'data_sources', ['source_name'])
    op.create_index('ix_clients_slug', 'clients', ['slug'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_clients_slug', table_name='clients')
    op.drop_index('ix_data_sources_source_name', table_name='data_sources')
    op.drop_index('ix_data_sources_client_id', table_name='data_sources')
    
    # Drop foreign key
    op.drop_constraint('fk_data_sources_client_id_clients', 'data_sources', type_='foreignkey')
    
    # Drop columns from data_sources
    op.drop_column('data_sources', 'source_name')
    op.drop_column('data_sources', 'client_id')
    
    # Drop clients table
    op.drop_table('clients')

