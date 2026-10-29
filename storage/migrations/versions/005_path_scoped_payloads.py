"""Allow byte-identical evidence from distinct source paths.

Revision ID: 005_path_scoped_payloads
Revises: 004_state_effective_week
"""
from alembic import op
import sqlalchemy as sa

revision = '005_path_scoped_payloads'
down_revision = '004_state_effective_week'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    names = {item['name'] for item in inspector.get_unique_constraints('source_payloads')}
    if 'source_payloads_content_sha256_key' in names:
        op.drop_constraint('source_payloads_content_sha256_key', 'source_payloads', type_='unique')
    indexes = {item['name'] for item in inspector.get_indexes('source_payloads')}
    if 'ix_source_payloads_hash' not in indexes:
        op.create_index('ix_source_payloads_hash', 'source_payloads', ['content_sha256'])


def downgrade():
    op.drop_index('ix_source_payloads_hash', table_name='source_payloads')
    op.create_unique_constraint('source_payloads_content_sha256_key', 'source_payloads', ['content_sha256'])
