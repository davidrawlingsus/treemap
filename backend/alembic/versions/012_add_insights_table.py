"""add insights table

Revision ID: 012
Revises: 011
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # Create insights table
    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=False),
        sa.Column('application', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('origins', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes
    op.create_index('ix_insights_client_id', 'insights', ['client_id'])
    op.create_index('ix_insights_type', 'insights', ['type'])
    op.create_index('ix_insights_created_at', 'insights', ['created_at'])
    # GIN index on origins JSONB column for efficient JSONB queries
    op.execute('CREATE INDEX ix_insights_origins ON insights USING GIN (origins)')


def downgrade():
    # Drop indexes
    op.drop_index('ix_insights_origins', table_name='insights')
    op.drop_index('ix_insights_created_at', table_name='insights')
    op.drop_index('ix_insights_type', table_name='insights')
    op.drop_index('ix_insights_client_id', table_name='insights')
    
    # Drop table
    op.drop_table('insights')
