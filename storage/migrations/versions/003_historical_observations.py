"""Preserve source-specific observations and unresolved identity reviews.

Revision ID: 003_historical_observations
Revises: 002_artifacts
"""
from alembic import op
from storage.models import fixture_observations, stat_observations, identity_reviews

revision = '003_historical_observations'
down_revision = '002_artifacts'
branch_labels = None
depends_on = None


def upgrade():
    for table in (fixture_observations, stat_observations, identity_reviews):
        table.create(op.get_bind(), checkfirst=False)


def downgrade():
    for table in (identity_reviews, stat_observations, fixture_observations):
        table.drop(op.get_bind(), checkfirst=False)
