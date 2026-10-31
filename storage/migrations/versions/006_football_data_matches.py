"""Separate Football-Data source bytes, verified team links and match observations.

Revision ID: 006_football_data_matches
Revises: 005_path_scoped_payloads
"""
from alembic import op
from storage.models import (football_data_imports, football_data_team_mappings,
                            football_data_matches)

revision = '006_football_data_matches'
down_revision = '005_path_scoped_payloads'
branch_labels = None
depends_on = None


def upgrade():
    for table in (football_data_imports, football_data_team_mappings,
                  football_data_matches):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in (football_data_matches, football_data_team_mappings,
                  football_data_imports):
        table.drop(op.get_bind(), checkfirst=False)
