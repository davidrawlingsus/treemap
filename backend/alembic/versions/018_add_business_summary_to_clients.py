"""add business_summary column to clients table

Revision ID: 018
Revises: 017
Create Date: 2025-12-31

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    # Add business_summary column to clients table
    op.add_column('clients', sa.Column('business_summary', sa.Text(), nullable=True))


def downgrade():
    # Remove business_summary column
    op.drop_column('clients', 'business_summary')

