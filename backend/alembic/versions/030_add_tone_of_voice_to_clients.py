"""add tone_of_voice column to clients table

Revision ID: 030
Revises: c9a3b99814ff
Create Date: 2026-01-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '030'
down_revision = 'c9a3b99814ff'
branch_labels = None
depends_on = None


def upgrade():
    # Add tone_of_voice column to clients table
    op.add_column('clients', sa.Column('tone_of_voice', sa.Text(), nullable=True))


def downgrade():
    # Remove tone_of_voice column
    op.drop_column('clients', 'tone_of_voice')
