"""rename prompt_text to system_message

Revision ID: 019
Revises: 018
Create Date: 2025-12-31 20:14:31.436477

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    # Rename prompt_text column to system_message in prompts table
    op.execute('ALTER TABLE prompts RENAME COLUMN prompt_text TO system_message')


def downgrade():
    # Rename system_message column back to prompt_text
    op.execute('ALTER TABLE prompts RENAME COLUMN system_message TO prompt_text')


