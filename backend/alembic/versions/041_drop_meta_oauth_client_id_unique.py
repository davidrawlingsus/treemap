"""Drop legacy unique on meta_oauth_tokens.client_id if present

Revision ID: 041
Revises: 040
Create Date: 2026-02-10

Production may have constraint meta_oauth_tokens_client_id_key (PG default name)
instead of uq_meta_oauth_tokens_client_id. Drop it so user-scoped tokens work.
"""
from alembic import op

revision = '041'
down_revision = '040'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE meta_oauth_tokens DROP CONSTRAINT IF EXISTS meta_oauth_tokens_client_id_key")


def downgrade():
    # No-op: we only dropped a legacy constraint; reverting would re-add old unique on client_id which we no longer want
    pass

