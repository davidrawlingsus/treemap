"""add prompt_type, prompt_message and helper prompts junction table

Revision ID: 026
Revises: 025
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    from sqlalchemy.engine import reflection
    
    # Check if columns already exist
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('prompts')]
    existing_tables = inspector.get_table_names()
    
    # Add prompt_type column to prompts table with default 'system' (if not exists)
    if 'prompt_type' not in existing_columns:
        op.add_column('prompts', sa.Column('prompt_type', sa.String(length=50), nullable=False, server_default='system'))
        # Update all existing rows to 'system'
        op.execute("UPDATE prompts SET prompt_type = 'system' WHERE prompt_type IS NULL")
    else:
        # Just ensure existing rows have the value
        op.execute("UPDATE prompts SET prompt_type = 'system' WHERE prompt_type IS NULL")
    
    # Add prompt_message column to prompts table (nullable) (if not exists)
    if 'prompt_message' not in existing_columns:
        op.add_column('prompts', sa.Column('prompt_message', sa.Text(), nullable=True))
    
    # Make system_message nullable (for helper prompts) - check current state first
    if 'system_message' in existing_columns:
        # Check if it's currently NOT NULL
        system_message_col = next((col for col in inspector.get_columns('prompts') if col['name'] == 'system_message'), None)
        if system_message_col and system_message_col.get('nullable') is False:
            op.alter_column('prompts', 'system_message', nullable=True)
    
    # Create prompt_helper_prompts junction table (if not exists)
    if 'prompt_helper_prompts' not in existing_tables:
        op.create_table(
            'prompt_helper_prompts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('system_prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('helper_prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['system_prompt_id'], ['prompts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['helper_prompt_id'], ['prompts.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('system_prompt_id', 'helper_prompt_id', name='uq_system_helper_prompt')
        )
        
        # Create index on system_prompt_id for faster lookups
        op.create_index('ix_prompt_helper_prompts_system_prompt_id', 'prompt_helper_prompts', ['system_prompt_id'])
        
        # Create index on helper_prompt_id for faster lookups
        op.create_index('ix_prompt_helper_prompts_helper_prompt_id', 'prompt_helper_prompts', ['helper_prompt_id'])
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('prompt_helper_prompts')]
        if 'ix_prompt_helper_prompts_system_prompt_id' not in existing_indexes:
            op.create_index('ix_prompt_helper_prompts_system_prompt_id', 'prompt_helper_prompts', ['system_prompt_id'])
        if 'ix_prompt_helper_prompts_helper_prompt_id' not in existing_indexes:
            op.create_index('ix_prompt_helper_prompts_helper_prompt_id', 'prompt_helper_prompts', ['helper_prompt_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_prompt_helper_prompts_helper_prompt_id', table_name='prompt_helper_prompts')
    op.drop_index('ix_prompt_helper_prompts_system_prompt_id', table_name='prompt_helper_prompts')
    
    # Drop junction table
    op.drop_table('prompt_helper_prompts')
    
    # Remove prompt_message column
    op.drop_column('prompts', 'prompt_message')
    
    # Remove prompt_type column
    op.drop_column('prompts', 'prompt_type')
    
    # Restore system_message to NOT NULL (assuming all prompts are system prompts after downgrade)
    op.execute("UPDATE prompts SET system_message = '' WHERE system_message IS NULL")
    op.alter_column('prompts', 'system_message', nullable=False)
