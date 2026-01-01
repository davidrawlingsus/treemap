"""add client_url column to clients table

Revision ID: 020
Revises: 019
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    # Add client_url column to clients table
    op.add_column('clients', sa.Column('client_url', sa.String(500), nullable=True))


def downgrade():
    # Remove client_url column
    op.drop_column('clients', 'client_url')

