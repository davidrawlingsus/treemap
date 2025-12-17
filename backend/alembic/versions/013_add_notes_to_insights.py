"""add notes column to insights table

Revision ID: 013
Revises: 012
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # Add notes column to insights table
    op.add_column('insights', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    # Remove notes column
    op.drop_column('insights', 'notes')
