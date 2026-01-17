"""add_all_clients_to_prompts

Revision ID: c9a3b99814ff
Revises: 029
Create Date: 2026-01-16 19:34:15.032919

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9a3b99814ff'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    # Check if column already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('prompts')]
    
    # Add all_clients column to prompts table with default False (if not exists)
    if 'all_clients' not in existing_columns:
        op.add_column('prompts', sa.Column('all_clients', sa.Boolean(), nullable=False, server_default='false'))
        # Update all existing rows to False
        op.execute("UPDATE prompts SET all_clients = false WHERE all_clients IS NULL")


def downgrade() -> None:
    # Remove all_clients column
    op.drop_column('prompts', 'all_clients')


