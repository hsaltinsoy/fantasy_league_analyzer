"""Immutable file evidence staging.

Revision ID: 002_artifacts
Revises: 001_initial
"""
from alembic import op
from storage.models import source_artifacts

revision = '002_artifacts'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    source_artifacts.create(op.get_bind(), checkfirst=False)
    op.execute("""
        CREATE FUNCTION source_artifacts_immutable_guard() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'immutable source artifact'; END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER source_artifacts_immutable_update
        BEFORE UPDATE OR DELETE ON source_artifacts
        FOR EACH ROW EXECUTE FUNCTION source_artifacts_immutable_guard()
    """)


def downgrade():
    source_artifacts.drop(op.get_bind(), checkfirst=False)
    op.execute('DROP FUNCTION IF EXISTS source_artifacts_immutable_guard()')
