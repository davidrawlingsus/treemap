"""meta_oauth_tokens: add user_id and scope by (user_id, client_id)

Revision ID: 040
Revises: 039
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '040'
down_revision = '039'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add user_id nullable first (idempotent)
    if 'user_id' not in [c['name'] for c in inspector.get_columns('meta_oauth_tokens')]:
        op.add_column(
            'meta_oauth_tokens',
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        )
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('meta_oauth_tokens')]
    if 'fk_meta_oauth_tokens_user_id' not in existing_fks:
        op.create_foreign_key(
            'fk_meta_oauth_tokens_user_id',
            'meta_oauth_tokens',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE',
        )

    # Backfill user_id from created_by
    op.execute("""
        UPDATE meta_oauth_tokens
        SET user_id = created_by
        WHERE created_by IS NOT NULL AND user_id IS NULL
    """)

    # Remove rows with no created_by (orphaned tokens)
    op.execute("DELETE FROM meta_oauth_tokens WHERE user_id IS NULL")

    # Make user_id non-nullable
    op.alter_column(
        'meta_oauth_tokens',
        'user_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Drop old unique on client_id only (if it exists)
    op.execute("ALTER TABLE meta_oauth_tokens DROP CONSTRAINT IF EXISTS uq_meta_oauth_tokens_client_id")

    # Add new unique on (user_id, client_id); drop first so re-run is safe
    op.execute("ALTER TABLE meta_oauth_tokens DROP CONSTRAINT IF EXISTS uq_meta_oauth_tokens_user_client")
    op.create_unique_constraint(
        'uq_meta_oauth_tokens_user_client',
        'meta_oauth_tokens',
        ['user_id', 'client_id'],
    )
    # Index (idempotent)
    op.execute("CREATE INDEX IF NOT EXISTS ix_meta_oauth_tokens_user_id_client_id ON meta_oauth_tokens (user_id, client_id)")


def downgrade():
    op.drop_index('ix_meta_oauth_tokens_user_id_client_id', table_name='meta_oauth_tokens')
    op.drop_constraint('uq_meta_oauth_tokens_user_client', 'meta_oauth_tokens', type_='unique')
    op.create_unique_constraint('uq_meta_oauth_tokens_client_id', 'meta_oauth_tokens', ['client_id'])
    op.drop_constraint('fk_meta_oauth_tokens_user_id', 'meta_oauth_tokens', type_='foreignkey')
    op.drop_column('meta_oauth_tokens', 'user_id')
