"""add dimension names table

Revision ID: 002
Revises: 001
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create dimension_names table
    op.create_table(
        'dimension_names',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ref_key', sa.String(length=100), nullable=False),
        sa.Column('custom_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('data_source_id', 'ref_key', name='uq_data_source_ref_key')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_dimension_names_data_source_id', 'dimension_names', ['data_source_id'])
    op.create_index('ix_dimension_names_ref_key', 'dimension_names', ['ref_key'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_dimension_names_ref_key', table_name='dimension_names')
    op.drop_index('ix_dimension_names_data_source_id', table_name='dimension_names')
    
    # Drop table
    op.drop_table('dimension_names')

