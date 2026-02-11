"""Add ad_library_only to clients for diagnosis-only brands

Revision ID: 045
Revises: 044
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa

revision = '045'
down_revision = '044'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'clients',
        sa.Column('ad_library_only', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade():
    op.drop_column('clients', 'ad_library_only')
