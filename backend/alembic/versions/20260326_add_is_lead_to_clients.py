"""add_is_lead_and_leadgen_run_id_to_clients

Revision ID: 16a026205ee8
Revises: 82e6f5230eab
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "16a026205ee8"
down_revision = "82e6f5230eab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("is_lead", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "clients",
        sa.Column("leadgen_run_id", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_clients_leadgen_run_id", "clients", ["leadgen_run_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_clients_leadgen_run_id", "clients", type_="unique")
    op.drop_column("clients", "leadgen_run_id")
    op.drop_column("clients", "is_lead")
