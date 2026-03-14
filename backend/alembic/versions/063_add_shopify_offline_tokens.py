"""add shopify offline token fields

Revision ID: 063
Revises: 062
Create Date: 2026-03-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "063"
down_revision: Union[str, Sequence[str], None] = "062"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shopify_store_connections",
        sa.Column("offline_access_token", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "shopify_store_connections",
        sa.Column("offline_access_scopes", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "shopify_store_connections",
        sa.Column("token_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shopify_store_connections", "token_updated_at")
    op.drop_column("shopify_store_connections", "offline_access_scopes")
    op.drop_column("shopify_store_connections", "offline_access_token")
