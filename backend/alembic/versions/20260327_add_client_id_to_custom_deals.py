"""Add client_id to custom_deals for co-branding with existing client logos

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'e9f0a1b2c3d4'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('custom_deals', sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=True))
    op.create_index('ix_custom_deals_client_id', 'custom_deals', ['client_id'])


def downgrade() -> None:
    op.drop_index('ix_custom_deals_client_id', table_name='custom_deals')
    op.drop_column('custom_deals', 'client_id')
