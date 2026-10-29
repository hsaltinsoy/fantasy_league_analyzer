"""Isolated PostgreSQL tests; never point at the live Phase 17 database."""
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select, func

from storage import models as m
from storage.import_artifacts import import_artifacts
from storage.normalize_history import Importer, normalize
from storage.history_quality import report, reconcile
from storage.history_repository import HistoricalRepository


@pytest.fixture(scope='module')
def engine():
    url = os.getenv('PHASE18_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set PHASE18_TEST_DATABASE_URL for isolated integration tests')
    if not url.endswith('/fantasy_league_phase18_test2'):
        pytest.fail('Phase 18 tests require the isolated fantasy_league_phase18_test2 database')
    db = create_engine(url, pool_pre_ping=True)
    import_artifacts('.', db)
    first = normalize(db)
    assert first['conflicts'] == []
    assert first['unresolved'] == []
    yield db
    db.dispose()


def test_idempotent_normalization_and_exact_row_reconciliation(engine):
    second = normalize(engine)
    assert second['counts']['player_gameweek_stats']['skipped'] == 5046
    assert second['counts']['player_gameweek_stats'].get('inserted', 0) == 0
    assert second['conflicts'] == []
    assert reconcile(engine)['status'] == 'passed'


def test_exact_identity_and_unresolved_external_mapping(engine):
    repository = HistoricalRepository(engine)
    assert repository.resolve_identity('tff', 10)['player_id'] == '10'
    assert repository.resolve_identity('xgedge', 10) is None
    with engine.connect() as db:
        assert db.execute(select(func.count()).select_from(m.identity_reviews)).scalar_one() == 572


def test_fixtures_stats_and_explicit_zero_minutes(engine):
    repository = HistoricalRepository(engine)
    fixtures = repository.fixtures_by_gameweek(1)
    assert len(fixtures) == 9
    assert all(row['home_team_id'] != row['away_team_id'] for row in fixtures)
    rows = repository.historical_player_statistics(10, before_week=10)
    assert len(rows) == 9
    with engine.connect() as db:
        linked = db.execute(select(func.count()).select_from(
            m.player_gameweek_stats.join(m.fixtures,
              m.player_gameweek_stats.c.fixture_id == m.fixtures.c.id)).where(
              m.player_gameweek_stats.c.gameweek_id == m.fixtures.c.gameweek_id)).scalar_one()
    assert linked == 5046
    assert report(engine)['explicit_zero_minute_results'] == 2512


def test_source_provenance_retains_identical_bytes_at_distinct_paths(engine):
    repository = HistoricalRepository(engine)
    row = repository.historical_player_statistics(10, before_week=2)[0]
    provenance = repository.provenance(row['source_payload_id'])
    assert provenance['source_path'] == 'historical_data/player_10.json'
    assert provenance['retrieved_at'] is None
    assert provenance['run_metadata']['retrieval_time_from_source'] is False
    with engine.connect() as db:
        duplicate_hashes = db.execute(select(func.count()).select_from(
            select(m.source_payloads.c.content_sha256).group_by(
                m.source_payloads.c.content_sha256).having(func.count() > 1).subquery())).scalar_one()
    assert duplicate_hashes > 0


def test_missing_fields_and_retrospective_position_evidence(engine):
    quality = report(engine)
    assert quality['historical_deadline_price_verified'] == 0
    assert quality['historical_deadline_availability_verified'] == 0
    assert quality['xg_xa_measurements_imported'] == 0
    assert quality['position_coverage_by_target_week']['9']['missing_from_572_player_roster'] > 0
    assert quality['rows_without_source_payload'] == {'fixtures': 0, 'player_gameweek_stats': 0,
                                                       'player_state': 0}


def test_chronological_queries_block_future_results_and_retrospective_evidence(engine):
    repository = HistoricalRepository(engine)
    rows = repository.historical_player_statistics(10, before_week=5)
    assert len(rows) == 4
    assert all(row['gameweek_id'] < 5 for row in rows)
    form = repository.player_form(10, target_week=5, previous_weeks=3)
    assert form['observations'] == 3
    assert form['mean_points'] == sum(row['fantasy_points'] for row in rows if row['gameweek_id'] >= 2) / 3
    historical_deadline = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert repository.historical_player_statistics(10, before_week=5, as_of=historical_deadline) == []
    assert repository.historical_states(10, before_week=5, as_of=historical_deadline) == []
    target = repository.players_by_gameweek(5, as_of=historical_deadline)
    assert len(target) == 572
    assert all(not player['position_evidence'] and not player['price_evidence'] for player in target)


def test_transfer_club_history_uses_fixture_evidence_not_current_club(engine):
    repository = HistoricalRepository(engine)
    before_seven = repository.positions_and_clubs(16, before_week=7)
    before_eight = repository.positions_and_clubs(16, before_week=8)
    assert any(row['effective_gameweek'] == 6 and row['team_id'] == '1' for row in before_seven)
    assert not any(row['effective_gameweek'] == 7 and row['team_id'] == '8' for row in before_seven)
    assert any(row['effective_gameweek'] == 7 and row['team_id'] == '8' for row in before_eight)


def test_conflict_report_does_not_overwrite_canonical_row(engine):
    with engine.begin() as db:
        name = db.execute(select(m.teams.c.name).where(m.teams.c.id == '1')).scalar_one()
        importer = Importer(db)
        state = importer.put(m.teams, {'id': '1'}, dict(
            id='1', name='INCONSISTENT NAME', source_id='tff_official', metadata=None))
        assert state == 'conflicting'
        assert importer.conflicts[0]['fields'] == ['name', 'metadata']
    with engine.connect() as db:
        assert db.execute(select(m.teams.c.name).where(m.teams.c.id == '1')).scalar_one() == name


def test_transaction_rollback(engine):
    with pytest.raises(RuntimeError, match='test rollback'):
        with engine.begin() as db:
            db.execute(m.data_sources.insert().values(
                id='phase18_rollback_probe', name='probe', kind='test'))
            raise RuntimeError('test rollback')
    with engine.connect() as db:
        assert db.execute(select(m.data_sources.c.id).where(
            m.data_sources.c.id == 'phase18_rollback_probe')).scalar_one_or_none() is None
