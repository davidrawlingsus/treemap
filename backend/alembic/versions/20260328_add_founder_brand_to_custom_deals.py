"""Add founder_brand to custom_deals

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('custom_deals', sa.Column('founder_brand', sa.String(50), nullable=True, server_default='mapthegap'))


def downgrade() -> None:
    op.drop_column('custom_deals', 'founder_brand')
