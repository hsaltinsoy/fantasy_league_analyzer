"""Relational storage schema. Raw evidence and immutable source text are retained."""
from sqlalchemy import (MetaData, Table, Column, Text, Integer, BigInteger, Numeric, Date, Time,
                        Boolean, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint, LargeBinary)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()


def table(name, *columns, **kwargs):
    return Table(name, metadata, *columns, **kwargs)


football_data_imports = table('football_data_imports',
    Column('id', Text, primary_key=True), Column('provider', Text, nullable=False),
    Column('season', Text, nullable=False), Column('original_filename', Text, nullable=False),
    Column('source_sha256', Text, nullable=False, unique=True),
    Column('raw_bytes', LargeBinary, nullable=False),
    Column('imported_at', DateTime(timezone=True), nullable=False),
    Column('row_count', Integer, nullable=False), Column('metadata', JSONB, nullable=False))
football_data_team_mappings = table('football_data_team_mappings',
    Column('provider_name', Text, primary_key=True),
    Column('team_id', Text, ForeignKey('teams.id'), nullable=False),
    Column('verification', Text, nullable=False),
    Column('evidence', Text, nullable=False))
football_data_matches = table('football_data_matches',
    Column('id', Text, primary_key=True),
    Column('import_id', Text, ForeignKey('football_data_imports.id'), nullable=False),
    Column('season', Text, nullable=False), Column('match_date', Date, nullable=False),
    Column('match_time', Time), Column('home_name', Text, nullable=False),
    Column('away_name', Text, nullable=False),
    Column('home_team_id', Text, ForeignKey('teams.id')),
    Column('away_team_id', Text, ForeignKey('teams.id')),
    Column('fixture_id', Text, ForeignKey('fixtures.id')),
    Column('home_goals', Integer), Column('away_goals', Integer),
    Column('full_time_result', Text), Column('half_home_goals', Integer),
    Column('half_away_goals', Integer), Column('half_time_result', Text),
    Column('home_xg', Numeric(10, 4)), Column('away_xg', Numeric(10, 4)),
    Column('home_shots', Integer), Column('away_shots', Integer),
    Column('home_sot', Integer), Column('away_sot', Integer),
    Column('raw_record', JSONB, nullable=False), Column('row_sha256', Text, nullable=False),
    UniqueConstraint('import_id', 'match_date', 'home_name', 'away_name'))


data_sources = table('data_sources', Column('id', Text, primary_key=True),
    Column('name', Text, nullable=False), Column('url', Text), Column('kind', Text, nullable=False),
    Column('metadata', JSONB))
collection_runs = table('collection_runs', Column('id', Text, primary_key=True),
    Column('source_id', Text, ForeignKey('data_sources.id')), Column('retrieved_at', DateTime(timezone=True), nullable=False),
    Column('status', Text, nullable=False), Column('content_hash', Text), Column('error', Text), Column('metadata', JSONB))
source_payloads = table('source_payloads', Column('id', Text, primary_key=True),
    Column('run_id', Text, ForeignKey('collection_runs.id')), Column('source_path', Text),
    Column('content_sha256', Text, nullable=False), Column('raw_payload', JSONB),
    Column('raw_text', Text), Column('retrieved_at', DateTime(timezone=True)), Column('evidence_quality', Text))
teams = table('teams', Column('id', Text, primary_key=True), Column('name', Text, nullable=False),
    Column('source_id', Text, ForeignKey('data_sources.id')), Column('metadata', JSONB))
players = table('players', Column('id', Text, primary_key=True), Column('name', Text, nullable=False),
    Column('source_id', Text, ForeignKey('data_sources.id')), Column('metadata', JSONB))
player_identity_mappings = table('player_identity_mappings', Column('id', Text, primary_key=True),
    Column('player_id', Text, ForeignKey('players.id')), Column('provider', Text, nullable=False),
    Column('provider_player_id', Text), Column('name_alias', Text), Column('confidence', Text, nullable=False),
    Column('version', Text), Column('valid_from', DateTime(timezone=True)),
    Column('valid_to', DateTime(timezone=True)), Column('evidence_id', Text, ForeignKey('source_payloads.id')))
gameweeks = table('gameweeks', Column('id', Integer, primary_key=True), Column('official_id', Text),
    Column('deadline_at', DateTime(timezone=True)), Column('deadline_source_id', Text, ForeignKey('data_sources.id')),
    Column('deadline_retrieved_at', DateTime(timezone=True)), Column('metadata', JSONB))
fixtures = table('fixtures', Column('id', Text, primary_key=True),
    Column('gameweek_id', Integer, ForeignKey('gameweeks.id'), nullable=False),
    Column('home_team_id', Text, ForeignKey('teams.id')), Column('away_team_id', Text, ForeignKey('teams.id')),
    Column('kickoff_at', DateTime(timezone=True)), Column('status', Text), Column('source_payload_id', Text, ForeignKey('source_payloads.id')),
    CheckConstraint('home_team_id IS NULL OR away_team_id IS NULL OR home_team_id <> away_team_id'))
match_results = table('match_results', Column('fixture_id', Text, ForeignKey('fixtures.id'), primary_key=True),
    Column('home_score', Integer), Column('away_score', Integer), Column('completed_at', DateTime(timezone=True)),
    Column('source_payload_id', Text, ForeignKey('source_payloads.id')))
player_gameweek_stats = table('player_gameweek_stats', Column('player_id', Text, ForeignKey('players.id'), primary_key=True),
    Column('gameweek_id', Integer, ForeignKey('gameweeks.id'), primary_key=True),
    Column('fixture_id', Text, ForeignKey('fixtures.id'), primary_key=True),
    Column('minutes', Integer), Column('fantasy_points', Numeric(10, 3)), Column('goals', Integer),
    Column('assists', Integer), Column('source_payload_id', Text, ForeignKey('source_payloads.id')),
    Column('metadata', JSONB))
player_state = table('player_state', Column('id', Text, primary_key=True),
    Column('player_id', Text, ForeignKey('players.id'), nullable=False), Column('gameweek_id', Integer, ForeignKey('gameweeks.id')),
    Column('effective_gameweek', Integer),
    Column('team_id', Text, ForeignKey('teams.id')), Column('position', Text), Column('price', Numeric(10, 3)),
    Column('availability', Text), Column('suspension', Text), Column('effective_at', DateTime(timezone=True)),
    Column('retrieved_at', DateTime(timezone=True), nullable=False),
    Column('evidence_quality', Text, nullable=False), Column('source_payload_id', Text, ForeignKey('source_payloads.id')),
    Column('metadata', JSONB))
forecast_models = table('forecast_models', Column('id', Text, primary_key=True),
    Column('name', Text, nullable=False), Column('version', Text, nullable=False),
    Column('experimental', Boolean, nullable=False), Column('configuration', JSONB),
    UniqueConstraint('name', 'version'))
forecast_runs = table('forecast_runs', Column('id', Text, primary_key=True),
    Column('model_id', Text, ForeignKey('forecast_models.id'), nullable=False),
    Column('gameweek_id', Integer, ForeignKey('gameweeks.id'), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False), Column('snapshot_id', Text),
    Column('configuration', JSONB), Column('status', Text, nullable=False))
player_forecasts = table('player_forecasts', Column('run_id', Text, ForeignKey('forecast_runs.id'), primary_key=True),
    Column('player_id', Text, ForeignKey('players.id'), primary_key=True),
    Column('expected_points', Numeric(12, 4)), Column('uncertainty', Numeric(12, 4)),
    Column('appearance_probability', Numeric(8, 6)), Column('metadata', JSONB))

# Exact legacy TEXT is retained alongside parsed timestamps to make reconciliation lossless.
snapshots = table('snapshots', Column('id', Text, primary_key=True),
    Column('gameweek', Integer, nullable=False), Column('captured_at_text', Text, nullable=False),
    Column('captured_at', DateTime(timezone=True), nullable=False), Column('deadline_at_text', Text),
    Column('deadline_at', DateTime(timezone=True)), Column('deadline_source', Text),
    Column('source_text', Text, nullable=False), Column('classification', Text, nullable=False),
    Column('payload_text', Text, nullable=False), Column('payload', JSONB, nullable=False),
    Column('source_sha256', Text, nullable=False))
predictions = table('predictions', Column('id', Text, primary_key=True),
    Column('snapshot_id', Text, ForeignKey('snapshots.id', ondelete='RESTRICT'), nullable=False),
    Column('gameweek', Integer, nullable=False), Column('created_at_text', Text, nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False), Column('status', Text, nullable=False),
    Column('model', Text, nullable=False), Column('model_version', Text, nullable=False),
    Column('risk_strategy', Text, nullable=False), Column('raw_expected_points', Numeric(14, 6), nullable=False),
    Column('risk_adjusted_objective', Numeric(14, 6)), Column('payload_text', Text, nullable=False),
    Column('payload', JSONB, nullable=False), Column('source_sha256', Text, nullable=False))
selections = table('selections', Column('prediction_id', Text, ForeignKey('predictions.id', ondelete='RESTRICT'), primary_key=True),
    Column('player_id', Text, primary_key=True), Column('slot', Integer, nullable=False),
    Column('role', Text, nullable=False), Column('captain', Boolean, nullable=False),
    Column('vice_captain', Boolean), Column('expected_points', Numeric(12, 4)),
    UniqueConstraint('prediction_id', 'role', 'slot'))
risk_solutions = table('risk_solutions', Column('prediction_id', Text, ForeignKey('predictions.id', ondelete='RESTRICT'), primary_key=True),
    Column('expected_point_floor', Numeric(12, 4)), Column('standard_deviation', Numeric(12, 4)),
    Column('solver_status', Text), Column('solver_bound', Numeric(12, 4)), Column('metadata', JSONB))
evaluation_runs = table('evaluation_runs', Column('id', Text, primary_key=True),
    Column('snapshot_id', Text, ForeignKey('snapshots.id', ondelete='RESTRICT'), nullable=False),
    Column('gameweek', Integer, nullable=False), Column('created_at_text', Text, nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False), Column('source_digest', Text, nullable=False),
    Column('status', Text, nullable=False), Column('source_text', Text, nullable=False),
    Column('payload_text', Text, nullable=False), Column('payload', JSONB, nullable=False),
    Column('source_sha256', Text, nullable=False), UniqueConstraint('snapshot_id', 'source_digest'))
official_player_results = table('official_player_results', Column('gameweek_id', Integer, ForeignKey('gameweeks.id'), primary_key=True),
    Column('player_id', Text, ForeignKey('players.id'), primary_key=True),
    Column('fantasy_points', Numeric(10, 3)), Column('source_payload_id', Text, ForeignKey('source_payloads.id')),
    Column('retrieved_at', DateTime(timezone=True), nullable=False))
model_evaluations = table('model_evaluations', Column('id', Text, primary_key=True),
    Column('run_id', Text, ForeignKey('evaluation_runs.id')), Column('model_id', Text, ForeignKey('forecast_models.id')),
    Column('gameweek_id', Integer, ForeignKey('gameweeks.id')), Column('evidence_quality', Text),
    Column('sample_count', Integer), Column('metrics', JSONB, nullable=False),
    Column('source_payload_id', Text, ForeignKey('source_payloads.id')))
historical_reports = table('historical_reports', Column('id', Text, primary_key=True),
    Column('report_type', Text, nullable=False), Column('source_path', Text, nullable=False),
    Column('content_sha256', Text, nullable=False), Column('content', JSONB, nullable=False),
    Column('evidence_quality', Text), Column('imported_at', DateTime(timezone=True), nullable=False),
    UniqueConstraint('source_path', 'content_sha256'))
source_artifacts = table('source_artifacts', Column('source_path', Text, primary_key=True),
    Column('content_sha256', Text, primary_key=True), Column('format', Text, nullable=False),
    Column('category', Text, nullable=False), Column('raw_bytes', LargeBinary, nullable=False),
    Column('imported_at', DateTime(timezone=True), nullable=False),
    Column('source_retrieved_at', DateTime(timezone=True)),
    Column('source_url', Text), Column('evidence_quality', Text), Column('metadata', JSONB))
fixture_observations = table('fixture_observations', Column('id', Text, primary_key=True),
    Column('fixture_id', Text, ForeignKey('fixtures.id'), nullable=False),
    Column('source_payload_id', Text, ForeignKey('source_payloads.id'), nullable=False),
    Column('gameweek_id', Integer, ForeignKey('gameweeks.id'), nullable=False),
    Column('home_team_id', Text, ForeignKey('teams.id')), Column('away_team_id', Text, ForeignKey('teams.id')),
    Column('status', Text), Column('home_score', Integer), Column('away_score', Integer),
    Column('source_quality', Text, nullable=False), Column('metadata', JSONB),
    UniqueConstraint('fixture_id', 'source_payload_id'))
stat_observations = table('stat_observations', Column('id', Text, primary_key=True),
    Column('player_id', Text, ForeignKey('players.id'), nullable=False),
    Column('gameweek_id', Integer, ForeignKey('gameweeks.id'), nullable=False),
    Column('fixture_id', Text, ForeignKey('fixtures.id')),
    Column('source_payload_id', Text, ForeignKey('source_payloads.id'), nullable=False),
    Column('fantasy_points', Numeric(10, 3)), Column('minutes', Integer),
    Column('goals', Integer), Column('assists', Integer),
    Column('source_quality', Text, nullable=False), Column('metadata', JSONB),
    UniqueConstraint('player_id', 'gameweek_id', 'fixture_id', 'source_payload_id'))
identity_reviews = table('identity_reviews', Column('id', Text, primary_key=True),
    Column('player_id', Text, ForeignKey('players.id')),
    Column('provider', Text, nullable=False), Column('provider_player_id', Text),
    Column('provider_name', Text), Column('reason', Text, nullable=False),
    Column('confidence', Text, nullable=False), Column('source_payload_id', Text, ForeignKey('source_payloads.id')),
    Column('candidate_ids', JSONB), Column('status', Text, nullable=False))

Index('ix_fixtures_week', fixtures.c.gameweek_id)
Index('ix_stats_week', player_gameweek_stats.c.gameweek_id)
Index('ix_player_state_week', player_state.c.gameweek_id, player_state.c.player_id)
Index('ix_player_state_effective_week', player_state.c.player_id, player_state.c.effective_gameweek)
Index('ix_predictions_week_model', predictions.c.gameweek, predictions.c.model)
Index('ix_evaluations_week', evaluation_runs.c.gameweek)
Index('ix_source_payloads_hash', source_payloads.c.content_sha256)
Index('ix_stat_observations_week', stat_observations.c.gameweek_id, stat_observations.c.player_id)
