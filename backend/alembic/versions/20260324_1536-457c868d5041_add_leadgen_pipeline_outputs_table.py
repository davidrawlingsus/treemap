"""add_leadgen_pipeline_outputs_table

Revision ID: 457c868d5041
Revises: c3d4e5f6a7b8
Create Date: 2026-03-24 15:36:13.707562

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '457c868d5041'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('leadgen_pipeline_outputs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('step_type', sa.String(length=50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('elapsed_seconds', sa.Float(), nullable=True),
        sa.Column('prompt_version_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['prompt_version_id'], ['prompts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['leadgen_voc_runs.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leadgen_pipeline_outputs_run_id'), 'leadgen_pipeline_outputs', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_leadgen_pipeline_outputs_run_id'), table_name='leadgen_pipeline_outputs')
    op.drop_table('leadgen_pipeline_outputs')
