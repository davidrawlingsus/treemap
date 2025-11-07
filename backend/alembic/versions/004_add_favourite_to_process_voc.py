"""add is_favourite to process_voc

Revision ID: 004
Revises: 003
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_favourite column to process_voc table
    op.add_column('process_voc', sa.Column('is_favourite', sa.Boolean(), nullable=True, server_default='false'))


def downgrade():
    # Remove is_favourite column from process_voc table
    op.drop_column('process_voc', 'is_favourite')

