"""add_top_level_ai_dropdown_to_prompts

Revision ID: d4e7f1a2b3c5
Revises: 065
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e7f1a2b3c5'
down_revision = '065'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect

    # Check if column already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('prompts')]

    if 'top_level_ai_dropdown' not in existing_columns:
        op.add_column('prompts', sa.Column('top_level_ai_dropdown', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('prompts', 'top_level_ai_dropdown')
