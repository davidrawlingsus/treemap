"""add dimension summaries table

Revision ID: 006
Revises: 005
Create Date: 2025-11-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'dimension_summaries' not in inspector.get_table_names():
        # Create dimension_summaries table
        op.create_table(
            'dimension_summaries',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('client_uuid', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('data_source', sa.String(length=255), nullable=False),
            sa.Column('dimension_ref', sa.String(length=50), nullable=False),
            sa.Column('dimension_name', sa.Text(), nullable=True),
            sa.Column('summary_text', sa.Text(), nullable=False),
            sa.Column('key_insights', postgresql.JSONB(), nullable=True),
            sa.Column('category_snapshot', postgresql.JSONB(), nullable=True),
            sa.Column('patterns', sa.Text(), nullable=True),
            sa.Column('sample_size', sa.Integer(), nullable=False),
            sa.Column('total_responses', sa.Integer(), nullable=False),
            sa.Column('model_used', sa.String(length=50), nullable=True),
            sa.Column('tokens_used', sa.Integer(), nullable=True),
            sa.Column('topic_distribution', postgresql.JSONB(), nullable=True),
            sa.Column('generation_duration_ms', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['client_uuid'], ['clients.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('client_uuid', 'data_source', 'dimension_ref', name='uq_client_source_dimension_summary')
        )
        
        # Create indexes for better query performance
        op.create_index('ix_dimension_summaries_client_uuid', 'dimension_summaries', ['client_uuid'])
        op.create_index('ix_dimension_summaries_data_source', 'dimension_summaries', ['data_source'])
        op.create_index('ix_dimension_summaries_dimension_ref', 'dimension_summaries', ['dimension_ref'])
    else:
        print("Table 'dimension_summaries' already exists, skipping creation.")


def downgrade():
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'dimension_summaries' in inspector.get_table_names():
        # Drop indexes
        op.drop_index('ix_dimension_summaries_dimension_ref', table_name='dimension_summaries')
        op.drop_index('ix_dimension_summaries_data_source', table_name='dimension_summaries')
        op.drop_index('ix_dimension_summaries_client_uuid', table_name='dimension_summaries')
        
        # Drop table
        op.drop_table('dimension_summaries')

