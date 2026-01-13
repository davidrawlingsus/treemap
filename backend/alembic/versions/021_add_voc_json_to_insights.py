"""add voc_json column to insights table

Revision ID: 021
Revises: 020
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    # Add voc_json column to insights table
    op.add_column('insights', sa.Column('voc_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove voc_json column
    op.drop_column('insights', 'voc_json')
