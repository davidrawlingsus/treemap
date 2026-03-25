"""add_clarity_replay_url

Revision ID: 82e6f5230eab
Revises: 457c868d5041
Create Date: 2026-03-25 00:46:58.140127

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '82e6f5230eab'
down_revision = '457c868d5041'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('widget_survey_responses', sa.Column('clarity_replay_url', sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column('widget_survey_responses', 'clarity_replay_url')
