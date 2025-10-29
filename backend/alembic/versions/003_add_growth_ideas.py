"""add growth ideas table

Revision ID: 003
Revises: 002
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'growth_ideas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_ref_key', sa.String(100), nullable=False),
        sa.Column('dimension_name', sa.String(255), nullable=True),
        sa.Column('idea_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generation_prompt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_growth_ideas_client_id',
        'growth_ideas', 'clients',
        ['client_id'], ['id']
    )
    
    op.create_foreign_key(
        'fk_growth_ideas_data_source_id',
        'growth_ideas', 'data_sources',
        ['data_source_id'], ['id']
    )
    
    # Create indexes for common queries
    op.create_index('ix_growth_ideas_client_id', 'growth_ideas', ['client_id'])
    op.create_index('ix_growth_ideas_data_source_id', 'growth_ideas', ['data_source_id'])
    op.create_index('ix_growth_ideas_status', 'growth_ideas', ['status'])
    op.create_index('ix_growth_ideas_dimension_ref_key', 'growth_ideas', ['dimension_ref_key'])


def downgrade() -> None:
    op.drop_index('ix_growth_ideas_dimension_ref_key', table_name='growth_ideas')
    op.drop_index('ix_growth_ideas_status', table_name='growth_ideas')
    op.drop_index('ix_growth_ideas_data_source_id', table_name='growth_ideas')
    op.drop_index('ix_growth_ideas_client_id', table_name='growth_ideas')
    op.drop_constraint('fk_growth_ideas_data_source_id', 'growth_ideas', type_='foreignkey')
    op.drop_constraint('fk_growth_ideas_client_id', 'growth_ideas', type_='foreignkey')
    op.drop_table('growth_ideas')

