"""add authorized emails

Revision ID: 027
Revises: 026
Create Date: 2026-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade():
    # Ensure pgcrypto extension is available for uuid generation
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create authorized_emails table
    op.create_table(
        "authorized_emails",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="authorized_emails_email_key"),
    )

    # Create authorized_email_clients association table
    op.create_table(
        "authorized_email_clients",
        sa.Column(
            "email_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["email_id"], ["authorized_emails.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("email_id", "client_id"),
    )
    op.create_index(
        "ix_authorized_email_clients_email_id",
        "authorized_email_clients",
        ["email_id"],
    )
    op.create_index(
        "ix_authorized_email_clients_client_id",
        "authorized_email_clients",
        ["client_id"],
    )


def downgrade():
    # Drop authorized email association table
    op.drop_index(
        "ix_authorized_email_clients_client_id",
        table_name="authorized_email_clients",
    )
    op.drop_index(
        "ix_authorized_email_clients_email_id",
        table_name="authorized_email_clients",
    )
    op.drop_table("authorized_email_clients")

    # Drop authorized_emails table
    op.drop_table("authorized_emails")

