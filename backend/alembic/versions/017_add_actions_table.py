"""add actions table

Revision ID: 017
Revises: 016
Create Date: 2025-12-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # Create actions table
    op.create_table(
        'actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prompt_text_sent', sa.Text(), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insight_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('ix_actions_prompt_id', 'actions', ['prompt_id'])
    op.create_index('ix_actions_client_id', 'actions', ['client_id'])
    op.create_index('ix_actions_created_at', 'actions', ['created_at'])
    # GIN index on insight_ids JSONB column for efficient JSONB queries
    op.execute('CREATE INDEX ix_actions_insight_ids ON actions USING GIN (insight_ids)')


def downgrade():
    # Drop indexes
    op.drop_index('ix_actions_insight_ids', table_name='actions')
    op.drop_index('ix_actions_created_at', table_name='actions')
    op.drop_index('ix_actions_client_id', table_name='actions')
    op.drop_index('ix_actions_prompt_id', table_name='actions')
    
    # Drop table
    op.drop_table('actions')

