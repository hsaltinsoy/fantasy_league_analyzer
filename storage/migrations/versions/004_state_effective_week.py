"""Explicit historical effective week for position and club evidence.

Revision ID: 004_state_effective_week
Revises: 003_historical_observations
"""
from alembic import op
import sqlalchemy as sa

revision = '004_state_effective_week'
down_revision = '003_historical_observations'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if 'effective_gameweek' not in {column['name'] for column in inspector.get_columns('player_state')}:
        op.add_column('player_state', sa.Column('effective_gameweek', sa.Integer(), nullable=True))
    if 'ix_player_state_effective_week' not in {index['name'] for index in inspector.get_indexes('player_state')}:
        op.create_index('ix_player_state_effective_week', 'player_state', ['player_id', 'effective_gameweek'])


def downgrade():
    op.drop_index('ix_player_state_effective_week', table_name='player_state')
    op.drop_column('player_state', 'effective_gameweek')
