"""add status column to insights table

Revision ID: 015
Revises: 014
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Add status column to insights table with default value
    op.add_column('insights', sa.Column('status', sa.String(length=50), nullable=True, server_default='Not Started'))


def downgrade():
    # Remove status column
    op.drop_column('insights', 'status')

