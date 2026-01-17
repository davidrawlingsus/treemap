"""add client_facing column to prompts and prompt_clients junction table

Revision ID: 029
Revises: 028
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    
    # Check if columns already exist
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('prompts')]
    existing_tables = inspector.get_table_names()
    
    # Add client_facing column to prompts table with default False (if not exists)
    if 'client_facing' not in existing_columns:
        op.add_column('prompts', sa.Column('client_facing', sa.Boolean(), nullable=False, server_default='false'))
        # Update all existing rows to False
        op.execute("UPDATE prompts SET client_facing = false WHERE client_facing IS NULL")
    
    # Create prompt_clients junction table (if not exists)
    if 'prompt_clients' not in existing_tables:
        op.create_table(
            'prompt_clients',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('prompt_id', 'client_id', name='uq_prompt_client')
        )
        
        # Create index on prompt_id for faster lookups
        op.create_index('ix_prompt_clients_prompt_id', 'prompt_clients', ['prompt_id'])
        
        # Create index on client_id for faster lookups
        op.create_index('ix_prompt_clients_client_id', 'prompt_clients', ['client_id'])
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('prompt_clients')]
        if 'ix_prompt_clients_prompt_id' not in existing_indexes:
            op.create_index('ix_prompt_clients_prompt_id', 'prompt_clients', ['prompt_id'])
        if 'ix_prompt_clients_client_id' not in existing_indexes:
            op.create_index('ix_prompt_clients_client_id', 'prompt_clients', ['client_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_prompt_clients_client_id', table_name='prompt_clients')
    op.drop_index('ix_prompt_clients_prompt_id', table_name='prompt_clients')
    
    # Drop junction table
    op.drop_table('prompt_clients')
    
    # Remove client_facing column
    op.drop_column('prompts', 'client_facing')
