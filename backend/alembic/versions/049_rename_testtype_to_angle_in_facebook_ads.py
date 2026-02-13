"""Rename testType to angle in facebook_ads full_json JSONB

Revision ID: 049
Revises: 048
Create Date: 2026-02-13

"""
from alembic import op

revision = '049'
down_revision = '048'
branch_labels = None
depends_on = None


def upgrade():
    # Rename 'testType' key to 'angle' inside the full_json JSONB column
    # for all facebook_ads rows that have a testType key
    op.execute("""
        UPDATE facebook_ads
        SET full_json = full_json - 'testType' || jsonb_build_object('angle', full_json->'testType')
        WHERE full_json ? 'testType';
    """)


def downgrade():
    # Revert: rename 'angle' key back to 'testType'
    op.execute("""
        UPDATE facebook_ads
        SET full_json = full_json - 'angle' || jsonb_build_object('testType', full_json->'angle')
        WHERE full_json ? 'angle';
    """)
