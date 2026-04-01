"""Add site_key to clients for public widget auth

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa
import secrets

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def _generate_site_key():
    return "site_" + secrets.token_urlsafe(16)


def upgrade():
    op.add_column('clients', sa.Column('site_key', sa.String(32), nullable=True))
    op.create_index('ix_clients_site_key', 'clients', ['site_key'], unique=True)

    # Backfill existing clients with unique site keys
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM clients WHERE site_key IS NULL")).fetchall()
    for row in rows:
        key = _generate_site_key()
        conn.execute(
            sa.text("UPDATE clients SET site_key = :key WHERE id = :id"),
            {"key": key, "id": row[0]},
        )


def downgrade():
    op.drop_index('ix_clients_site_key', table_name='clients')
    op.drop_column('clients', 'site_key')
