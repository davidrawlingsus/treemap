"""add verbatims column to insights table

Revision ID: 014
Revises: 013
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # Add verbatims column to insights table
    op.add_column('insights', sa.Column('verbatims', JSONB(), nullable=True, server_default='[]'))


def downgrade():
    # Remove verbatims column
    op.drop_column('insights', 'verbatims')
