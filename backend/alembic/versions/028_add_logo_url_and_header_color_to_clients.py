"""add logo_url and header_color columns to clients table

Revision ID: 028
Revises: 027
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade():
    # Add logo_url and header_color columns to clients table
    op.add_column('clients', sa.Column('logo_url', sa.String(500), nullable=True))
    op.add_column('clients', sa.Column('header_color', sa.String(7), nullable=True))


def downgrade():
    # Remove logo_url and header_color columns
    op.drop_column('clients', 'header_color')
    op.drop_column('clients', 'logo_url')
