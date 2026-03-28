"""Add success_message to deal_page_defaults

Revision ID: d9c912b3a6e7
Revises: a2b3c4d5e6f7
Create Date: 2026-03-27 17:43:07.770601

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd9c912b3a6e7'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('deal_page_defaults', sa.Column('success_message', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('deal_page_defaults', 'success_message')
