"""normalize Hero Concept type values in insights table

Revision ID: 031
Revises: 030
Create Date: 2026-01-19

Changes 'Hero Concept #1', 'Hero Concept #2', etc. to just 'Hero Concept'
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    # Update any type containing 'Hero Concept #' followed by a number to just 'Hero Concept'
    op.execute("""
        UPDATE insights 
        SET type = 'Hero Concept' 
        WHERE type ~ '^Hero Concept #[0-9]+$'
    """)


def downgrade():
    # Cannot reliably downgrade since we don't know what the original numbers were
    pass
