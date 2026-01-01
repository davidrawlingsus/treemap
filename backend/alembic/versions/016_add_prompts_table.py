"""add prompts table

Revision ID: 016
Revises: 015
Create Date: 2025-12-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('prompt_purpose', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='test'),
        sa.Column('llm_model', sa.String(length=100), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_prompt_name_version')
    )
    
    # Create indexes
    op.create_index('ix_prompts_status', 'prompts', ['status'])
    op.create_index('ix_prompts_prompt_purpose', 'prompts', ['prompt_purpose'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_prompts_prompt_purpose', table_name='prompts')
    op.drop_index('ix_prompts_status', table_name='prompts')
    
    # Drop table
    op.drop_table('prompts')

