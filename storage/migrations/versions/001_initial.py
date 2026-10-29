"""Initial PostgreSQL schema for read-only migration comparison.

Revision ID: 001_initial
Revises:
"""
from alembic import op
from storage.models import metadata

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    later = {'source_artifacts', 'fixture_observations', 'stat_observations', 'identity_reviews'}
    initial_tables = [table for table in metadata.sorted_tables if table.name not in later]
    metadata.create_all(op.get_bind(), tables=initial_tables, checkfirst=False)
    for name in ('snapshots', 'predictions', 'evaluation_runs'):
        op.execute(f"""
        CREATE FUNCTION {name}_immutable_guard() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'immutable {name}'; END;
        $$ LANGUAGE plpgsql
        """)
        op.execute(f"""
        CREATE TRIGGER {name}_immutable_update BEFORE UPDATE OR DELETE ON {name}
        FOR EACH ROW EXECUTE FUNCTION {name}_immutable_guard()
        """)


def downgrade():
    later = {'source_artifacts', 'fixture_observations', 'stat_observations', 'identity_reviews'}
    initial_tables = [table for table in metadata.sorted_tables if table.name not in later]
    metadata.drop_all(op.get_bind(), tables=initial_tables, checkfirst=False)
    for name in ('snapshots', 'predictions', 'evaluation_runs'):
        op.execute(f'DROP FUNCTION IF EXISTS {name}_immutable_guard()')
