"""Add pause_cancel_text and no_charge_text to custom_deals

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'f0a1b2c3d4e5'
down_revision = 'e9f0a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('custom_deals', sa.Column('pause_cancel_text', sa.Text, nullable=True))
    op.add_column('custom_deals', sa.Column('no_charge_text', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column('custom_deals', 'no_charge_text')
    op.drop_column('custom_deals', 'pause_cancel_text')
