"""add_client_id_to_api_keys

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add client_id as nullable first, then make it non-null after backfill if needed
    op.add_column('api_keys', sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False))
    op.create_index('ix_api_keys_client_id', 'api_keys', ['client_id'])


def downgrade() -> None:
    op.drop_index('ix_api_keys_client_id', table_name='api_keys')
    op.drop_column('api_keys', 'client_id')
