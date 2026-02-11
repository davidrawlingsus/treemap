"""add context_menu_groups table and context_menu_group_id to prompts

Revision ID: 042
Revises: 041
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '042'
down_revision = '041'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create context_menu_groups table if not exists
    if 'context_menu_groups' not in existing_tables:
        op.create_table(
            'context_menu_groups',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('label', sa.String(length=255), nullable=False),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

    # Seed default "AI Expert" group if not exists
    op.execute("""
        INSERT INTO context_menu_groups (id, label, sort_order)
        SELECT gen_random_uuid(), 'AI Expert', 0
        WHERE NOT EXISTS (SELECT 1 FROM context_menu_groups WHERE label = 'AI Expert')
    """)

    # Add context_menu_group_id to prompts if not exists
    existing_columns = [col['name'] for col in inspector.get_columns('prompts')]
    if 'context_menu_group_id' not in existing_columns:
        op.add_column(
            'prompts',
            sa.Column('context_menu_group_id', postgresql.UUID(as_uuid=True), nullable=True)
        )
        op.execute("""
            UPDATE prompts
            SET context_menu_group_id = (SELECT id FROM context_menu_groups WHERE label = 'AI Expert' LIMIT 1)
            WHERE client_facing = true AND context_menu_group_id IS NULL
        """)
        op.create_foreign_key(
            'fk_prompts_context_menu_group_id',
            'prompts',
            'context_menu_groups',
            ['context_menu_group_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    op.drop_constraint('fk_prompts_context_menu_group_id', 'prompts', type_='foreignkey')
    op.drop_column('prompts', 'context_menu_group_id')
    op.drop_table('context_menu_groups')
