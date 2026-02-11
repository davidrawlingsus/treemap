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
    # Add user_id nullable first
    op.add_column(
        'meta_oauth_tokens',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
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
        WHERE created_by IS NOT NULL
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

    # Drop old unique on client_id only
    op.drop_constraint('uq_meta_oauth_tokens_client_id', 'meta_oauth_tokens', type_='unique')

    # Add new unique on (user_id, client_id)
    op.create_unique_constraint(
        'uq_meta_oauth_tokens_user_client',
        'meta_oauth_tokens',
        ['user_id', 'client_id'],
    )
    op.create_index(
        'ix_meta_oauth_tokens_user_id_client_id',
        'meta_oauth_tokens',
        ['user_id', 'client_id'],
    )


def downgrade():
    op.drop_index('ix_meta_oauth_tokens_user_id_client_id', table_name='meta_oauth_tokens')
    op.drop_constraint('uq_meta_oauth_tokens_user_client', 'meta_oauth_tokens', type_='unique')
    op.create_unique_constraint('uq_meta_oauth_tokens_client_id', 'meta_oauth_tokens', ['client_id'])
    op.drop_constraint('fk_meta_oauth_tokens_user_id', 'meta_oauth_tokens', type_='foreignkey')
    op.drop_column('meta_oauth_tokens', 'user_id')
