"""add origin and voc_json columns to actions table

Revision ID: 022
Revises: 021
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade():
    # Add origin and voc_json columns to actions table
    op.add_column('actions', sa.Column('origin', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('actions', sa.Column('voc_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove origin and voc_json columns
    op.drop_column('actions', 'voc_json')
    op.drop_column('actions', 'origin')
