"""make insight type column nullable

Revision ID: 024
Revises: 023
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    # Make type column nullable
    op.alter_column('insights', 'type',
                    existing_type=sa.String(length=100),
                    nullable=True)


def downgrade():
    # Make type column non-nullable again (set default for existing nulls first)
    op.execute("UPDATE insights SET type = '' WHERE type IS NULL")
    op.alter_column('insights', 'type',
                    existing_type=sa.String(length=100),
                    nullable=False)
