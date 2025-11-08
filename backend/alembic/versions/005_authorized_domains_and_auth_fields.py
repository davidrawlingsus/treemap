"""add authorized domains and auth fields

Revision ID: 005
Revises: 004
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    # Ensure pgcrypto extension is available for uuid generation
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create authorized_domains table
    op.create_table(
        "authorized_domains",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("domain", sa.String(length=255), nullable=False),
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
        sa.UniqueConstraint("domain", name="authorized_domains_domain_key"),
    )

    # Create authorized_domain_clients association table
    op.create_table(
        "authorized_domain_clients",
        sa.Column(
            "domain_id",
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
            ["domain_id"], ["authorized_domains.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("domain_id", "client_id"),
    )
    op.create_index(
        "ix_authorized_domain_clients_domain_id",
        "authorized_domain_clients",
        ["domain_id"],
    )
    op.create_index(
        "ix_authorized_domain_clients_client_id",
        "authorized_domain_clients",
        ["client_id"],
    )

    # Extend users table with auth-related fields
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_magic_link_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("magic_link_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "magic_link_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_users_magic_link_token",
        "users",
        ["magic_link_token"],
        unique=False,
    )

    # Extend memberships table with provisioning audit fields
    op.add_column(
        "memberships",
        sa.Column(
            "provisioned_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "memberships",
        sa.Column(
            "provisioned_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "memberships",
        sa.Column("provisioning_method", sa.String(length=50), nullable=True),
    )
    op.create_foreign_key(
        "fk_memberships_provisioned_by_users",
        "memberships",
        "users",
        ["provisioned_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_memberships_provisioned_by",
        "memberships",
        ["provisioned_by"],
        unique=False,
    )
    op.create_index(
        "ix_memberships_provisioned_at",
        "memberships",
        ["provisioned_at"],
        unique=False,
    )


def downgrade():
    # Revert membership changes
    op.drop_index("ix_memberships_provisioned_at", table_name="memberships")
    op.drop_index("ix_memberships_provisioned_by", table_name="memberships")
    op.drop_constraint(
        "fk_memberships_provisioned_by_users", "memberships", type_="foreignkey"
    )
    op.drop_column("memberships", "provisioning_method")
    op.drop_column("memberships", "provisioned_by")
    op.drop_column("memberships", "provisioned_at")

    # Revert user auth fields
    op.drop_index("ix_users_magic_link_token", table_name="users")
    op.drop_column("users", "magic_link_expires_at")
    op.drop_column("users", "magic_link_token")
    op.drop_column("users", "last_magic_link_sent_at")
    op.drop_column("users", "hashed_password")

    # Drop authorized domain association table
    op.drop_index(
        "ix_authorized_domain_clients_client_id",
        table_name="authorized_domain_clients",
    )
    op.drop_index(
        "ix_authorized_domain_clients_domain_id",
        table_name="authorized_domain_clients",
    )
    op.drop_table("authorized_domain_clients")

    # Drop authorized_domains table
    op.drop_table("authorized_domains")


