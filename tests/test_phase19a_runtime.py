"""Phase 19A writes only to the dedicated PostgreSQL test database."""
import os
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select

from storage.runtime_repository import RuntimeRepository
from storage.repository import TrackingRepository
from storage.models import player_state, snapshots


@pytest.fixture(scope='module')
def repositories():
    url = os.getenv('PHASE17_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Dedicated PostgreSQL test URL required')
    if not url.endswith('/fantasy_league_phase17_test'):
        pytest.fail('Refusing writes outside dedicated PostgreSQL test database')
    engine = create_engine(url, pool_pre_ping=True)
    yield RuntimeRepository(engine), TrackingRepository(engine)
    engine.dispose()


def test_current_player_ingestion_idempotent(repositories):
    current, _ = repositories
    feed = {'players': [{'id': 'phase19a-test-player', 'name': 'Test Player',
        'club_id': 'phase19a-test-club', 'position': 'MID', 'price': 7,
        'availability': 'available'}], 'raw_payload': {'test': 'phase19a'},
        'retrieved_at': datetime(2026, 10, 30, tzinfo=timezone.utc),
        'source_url': 'https://example.invalid/test'}
    first = current.ingest_current_players(feed)
    second = current.ingest_current_players(feed)
    assert first['source_payload_id'] == second['source_payload_id']
    assert second['inserted'] == 0 and second['skipped'] == 1
    players = [p for p in current.current_players() if p['id'] == 'phase19a-test-player']
    assert len(players) == 1 and players[0]['state']['price'] == 7


def test_fixture_ingestion_idempotent(repositories):
    current, _ = repositories
    feed = {'raw_payload': {'test': 'phase19a-fixture'},
        'captured_utc': '2026-10-30T00:00:00+00:00',
        'source_url': 'https://example.invalid/fixtures',
        'weeks': {'99': {'gameweek_id': 'phase19a-week', 'deadline': None,
            'matches': [{'id': 'phase19a-fixture', 'homeClubId': 'phase19a-home',
                'awayClubId': 'phase19a-away', 'kickoffAt': '2026-11-01T12:00:00+00:00',
                'status': 'SCHEDULED', 'homeScore': None, 'awayScore': None}]}}}
    first = current.ingest_current_fixtures(feed)
    second = current.ingest_current_fixtures(feed)
    assert first['inserted'] + first['skipped'] == 1 and second['skipped'] == 1
    assert current.fixtures_by_gameweek(99)[0]['id'] == 'phase19a-fixture'
    changed = {**feed, 'raw_payload': {'test': 'phase19a-fixture-conflict'},
        'weeks': {'99': {**feed['weeks']['99'], 'matches': [
            {**feed['weeks']['99']['matches'][0], 'homeClubId': 'phase19a-other'}]}}}
    conflict = current.ingest_current_fixtures(changed)
    assert conflict['conflicting'] == 1 and conflict['inserted'] == 0


def test_ingestion_provenance_and_rollback(repositories):
    from sqlalchemy import func
    from storage import models as m
    current, _ = repositories
    with current.engine.connect() as db:
        player_count = db.execute(select(func.count()).select_from(m.player_state).where(
            m.player_state.c.evidence_quality == 'current_official_api')).scalar_one()
        fixture_count = db.execute(select(func.count()).select_from(m.fixture_observations).where(
            m.fixture_observations.c.source_quality == 'current_official_api')).scalar_one()
        evidence = db.execute(select(m.source_payloads.c.raw_payload,
            m.source_payloads.c.retrieved_at).where(
            m.source_payloads.c.evidence_quality == 'current_official_api')).all()
    assert player_count >= 1 and fixture_count >= 1
    assert evidence and all(raw is not None and timestamp.tzinfo is not None
                            for raw, timestamp in evidence)
    feed = {'players': [{'id': 'phase19a-rollback-player', 'name': 'Rollback',
        'club_id': None, 'position': 'MID', 'price': 3}, {'name': 'Invalid'}],
        'raw_payload': {'test': 'rollback'},
        'retrieved_at': datetime(2026, 10, 30, 1, tzinfo=timezone.utc),
        'source_url': 'https://example.invalid/rollback'}
    with pytest.raises(KeyError):
        current.ingest_current_players(feed)
    with current.engine.connect() as db:
        assert db.execute(select(m.players.c.id).where(
            m.players.c.id == 'phase19a-rollback-player')).scalar_one_or_none() is None


def test_runtime_rebuilds_official_inputs_from_raw_payloads(repositories):
    current, _ = repositories
    raw_players = [{'playerId': 99001, 'name': 'Raw', 'surname': 'Player',
        'clubId': 9901, 'position': 'MID', 'cost': 6.5,
        'availabilityStatus': 'available'}]
    current.ingest_current_players({'players': [{'id': 99001, 'name': 'Raw Player',
        'club_id': 9901, 'position': 'MID', 'price': 6.5,
        'availability': 'available'}], 'raw_payload': raw_players,
        'retrieved_at': datetime(2026, 10, 30, 2, tzinfo=timezone.utc),
        'source_url': 'https://example.invalid/players'})
    assert current.current_player_pool()[0]['id'] == 99001
    raw_fixtures = {'data': {'gameweeks': [{'id': 99001, 'order': 98,
        'deadline': '2098-01-02T00:00:00Z', 'matches': [{
            'id': 99001, 'homeClubId': 9901, 'awayClubId': 9902,
            'kickoffAt': '2098-01-03T00:00:00Z', 'status': 'SCHEDULED'}]}]}}
    current.ingest_current_fixtures({'raw_payload': raw_fixtures,
        'captured_utc': '2026-10-30T02:00:00+00:00',
        'source_url': 'https://example.invalid/fixtures',
        'weeks': {'98': {'gameweek_id': 99001, 'deadline': '2098-01-02T00:00:00Z',
            'matches': raw_fixtures['data']['gameweeks'][0]['matches']}}})
    assert current.fixture_archive()['weeks']['98']['matches'][0]['id'] == 99001


def test_conflicting_immutable_snapshot_rejected(repositories):
    _, tracking = repositories
    row = {'id': 'phase19a-test-snapshot', 'gameweek': 99,
        'captured_at': '2026-10-30T00:00:00+00:00', 'deadline_at': None,
        'deadline_source': None, 'source': '{}', 'classification': 'test', 'payload': '{}'}
    tracking.save_snapshot(row)
    tracking.save_snapshot(row)
    with pytest.raises(ValueError, match='Conflicting immutable snapshot'):
        tracking.save_snapshot({**row, 'payload': '{"changed":true}'})
    assert tracking.get_snapshot(row['id'])['payload'] == {}


def test_benchmark_report_parity_on_frozen_tracking(monkeypatch, repositories):
    from analysis.live_benchmark import report
    url = os.environ['PHASE17_TEST_DATABASE_URL']
    monkeypatch.setenv('STORAGE_BACKEND', 'sqlite')
    old = report()
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    new = report()
    def normalize(value):
        if isinstance(value, float):
            return round(value, 6)
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        return value
    assert normalize(new) == normalize(old)


def test_benchmark_postgres_failure_has_no_sqlite_fallback(monkeypatch):
    from app import create_app
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    response = create_app().test_client().get('/benchmark')
    assert response.status_code == 503
    assert 'PostgreSQL benchmark unavailable' in response.get_json()['error']


def test_dashboard_and_lineup_postgres_failure_no_file_fallback(monkeypatch):
    from app import create_app
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    client = create_app().test_client()
    for route in ('/', '/api/lineup/latest?week=11'):
        response = client.get(route)
        assert response.status_code == 503
        assert 'PostgreSQL' in response.get_json()['error']


def test_benchmark_page_uses_postgres(monkeypatch, repositories):
    from app import create_app
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE17_TEST_DATABASE_URL'])
    response = create_app().test_client().get('/benchmark')
    assert response.status_code == 200
    assert b'benchmark' in response.data.lower()


def test_prediction_batch_rollback_and_concurrent_duplicate(repositories):
    _, tracking = repositories
    base = {'id': 'phase19a-test-prediction', 'snapshot_id': 'phase19a-test-snapshot',
        'gameweek': 99, 'created_at': '2026-10-30T00:01:00+00:00', 'status': 'deadline_unknown',
        'model': 'phase19a-test', 'model_version': '1', 'risk_strategy': 'test',
        'raw_expected_points': 10.0, 'risk_adjusted_objective': None, 'payload': '{}'}
    invalid = {**base, 'id': 'phase19a-invalid', 'snapshot_id': 'missing-snapshot'}
    with pytest.raises(ValueError, match='Unknown snapshot'):
        tracking.save_predictions([base, invalid])
    assert tracking.get_prediction(base['id']) is None
    def write(index):
        return tracking.save_predictions([{**base, 'id': f'phase19a-concurrent-{index}'}])[0]['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(write, range(2)))
    assert ids[0] == ids[1]


def test_postgres_prospective_capture_and_evaluation(monkeypatch, repositories):
    from analysis import prospective_monitor as monitor, live_benchmark
    from analysis.prediction_tracking import latest_evaluation_run
    from analysis.benchmark_evaluation import PLAYER_HISTORY_URL
    from data_sources.tff_official import BASE
    from datetime import timedelta
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE17_TEST_DATABASE_URL'])
    sqlite_source = Path('historical_data/prediction_tracking.sqlite3')
    sqlite_before = hashlib.sha256(sqlite_source.read_bytes()).hexdigest()
    now = datetime(2098, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr('analysis.prediction_tracking.utc_now', lambda: now.isoformat())
    endpoint = BASE + live_benchmark.FIXTURE_ENDPOINT
    match = {'id': 98001, 'homeClubId': 9801, 'awayClubId': 9802,
             'kickoffAt': (now + timedelta(days=2)).isoformat(),
             'status': 'SCHEDULED', 'homeScore': None, 'awayScore': None}
    archive = {'source_endpoint': live_benchmark.FIXTURE_ENDPOINT,
               'source_url': endpoint, 'captured_utc': now.isoformat(),
               'weeks': {'98': {'gameweek_id': 98001,
               'deadline': (now + timedelta(days=1)).isoformat(), 'matches': [match]}}}
    players = [{'id': i, 'name': f'P{i}', 'position': 'MID', 'club_id': 9801,
                'price': 4} for i in range(98001, 98016)]
    records = [(p, [{'gameweekOrder': 97, 'points': 2, 'minutesPlayed': 90}]) for p in players]
    monkeypatch.setattr(live_benchmark, 'load_crosswalk', lambda: {})
    monkeypatch.setattr(live_benchmark, 'crosswalk_version', lambda _: 'test')
    monkeypatch.setattr('analysis.team_of_week_v36.load', lambda _: {})
    def predict(week, pool, history, fixtures, tow, model='short_form_3w', **kwargs):
        if kwargs.get('experimental_covariance'):
            raise ValueError('No covariance clusters')
        return {'week': week, 'model': model, 'risk_profile': 'balanced',
                'starting_xi': [dict(p, team='9801', opponent='9802', xpts=2.0,
                                     captain=p['id'] == 98001) for p in pool[:11]],
                'bench': pool[11:], 'formation': '4-4-2'}
    monkeypatch.setattr(live_benchmark, 'predict', predict)
    first = monitor.capture(fixture_archive=archive, now=now,
        players_provider=lambda: {'players': players}, records_provider=lambda: records)
    second = monitor.capture(fixture_archive=archive, now=now,
        players_provider=lambda: pytest.fail('Repeated capture fetched players'))
    assert first['status'] in ('captured', 'already_captured') and first['gameweek'] == 98
    assert second['status'] == 'already_captured' and second['snapshot_id'] == first['snapshot_id']
    assert len(repositories[1].prediction_ids(first['snapshot_id'])) == (
        first['predictions_created'] if first['status'] == 'captured' else 5)
    prior_run = latest_evaluation_run(first['snapshot_id'])
    pending = monitor.evaluate(gameweek=98, fixture_archive=archive)
    assert pending['status'] == 'not_ready'
    assert latest_evaluation_run(first['snapshot_id']) == prior_run
    finished = {**archive, 'weeks': {'98': {**archive['weeks']['98'],
        'matches': [{**match, 'status': 'FT', 'homeScore': 1, 'awayScore': 0}]}}}
    def rows_provider(week, ids):
        return {'source_url': PLAYER_HISTORY_URL, 'retrieved_at': now.isoformat(),
                'rows_by_player': {str(pid): [{'gameweekOrder': 98, 'gameweekId': 98001,
                    'opponentClubId': 9802, 'homeAway': 'H', 'points': 2.0}] for pid in ids}}
    missing = monitor.evaluate(gameweek=98, fixture_archive=finished,
        rows_provider=lambda week, ids: {'source_url': PLAYER_HISTORY_URL,
            'retrieved_at': now.isoformat(), 'rows_by_player': {}})
    assert missing['status'] != 'complete'
    completed = monitor.evaluate(gameweek=98, fixture_archive=finished,
                                  rows_provider=rows_provider)
    repeated = monitor.evaluate(gameweek=98, fixture_archive=finished,
                                 rows_provider=rows_provider)
    assert completed['status'] == repeated['status'] == 'complete'
    assert completed['evaluation_run_id'] == repeated['evaluation_run_id']
    assert hashlib.sha256(sqlite_source.read_bytes()).hexdigest() == sqlite_before


def test_postgres_model_failure_leaves_no_snapshot(monkeypatch, repositories):
    from analysis import prospective_monitor as monitor, live_benchmark
    from data_sources.tff_official import BASE
    from datetime import timedelta
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE17_TEST_DATABASE_URL'])
    now = datetime(2098, 2, 1, tzinfo=timezone.utc)
    endpoint = BASE + live_benchmark.FIXTURE_ENDPOINT
    archive = {'source_endpoint': live_benchmark.FIXTURE_ENDPOINT,
        'source_url': endpoint, 'captured_utc': now.isoformat(),
        'weeks': {'97': {'gameweek_id': 97001,
            'deadline': (now + timedelta(days=1)).isoformat(),
            'matches': [{'id': 97001, 'homeClubId': 9701, 'awayClubId': 9702,
                'kickoffAt': (now + timedelta(days=2)).isoformat(), 'status': 'SCHEDULED'}]}}}
    players = [{'id': i, 'name': f'P{i}', 'position': 'MID', 'club_id': 9701,
                'price': 4} for i in range(97001, 97016)]
    monkeypatch.setattr(live_benchmark, 'load_crosswalk', lambda: {})
    monkeypatch.setattr(live_benchmark, 'crosswalk_version', lambda _: 'test')
    monkeypatch.setattr('analysis.team_of_week_v36.load', lambda _: {})
    monkeypatch.setattr(live_benchmark, 'predict', lambda *args, **kwargs:
        (_ for _ in ()).throw(RuntimeError('Synthetic model failure')))
    from sqlalchemy import func
    from storage import models as m
    with repositories[0].engine.connect() as db:
        before = db.execute(select(func.count()).select_from(m.snapshots).where(
            m.snapshots.c.gameweek == 97)).scalar_one()
    with pytest.raises(RuntimeError, match='Synthetic model failure'):
        monitor.capture(fixture_archive=archive, now=now,
            players_provider=lambda: {'players': players}, records_provider=lambda: [])
    with repositories[0].engine.connect() as db:
        after = db.execute(select(func.count()).select_from(m.snapshots).where(
            m.snapshots.c.gameweek == 97)).scalar_one()
    assert before == after


def test_fixture_api_failure_creates_no_postgres_capture(monkeypatch, repositories):
    from analysis import prospective_monitor as monitor
    from data_sources.tff_official import TFFFeedError
    from sqlalchemy import func
    from storage import models as m
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE17_TEST_DATABASE_URL'])
    monkeypatch.setattr(monitor.live_benchmark, 'fetch_official_fixtures',
        lambda: (_ for _ in ()).throw(TFFFeedError('Synthetic fixture API failure')))
    with repositories[0].engine.connect() as db:
        before = db.execute(select(func.count()).select_from(m.snapshots)).scalar_one()
    with pytest.raises(TFFFeedError, match='Synthetic fixture API failure'):
        monitor.capture()
    with repositories[0].engine.connect() as db:
        assert db.execute(select(func.count()).select_from(m.snapshots)).scalar_one() == before


def test_capture_transaction_rolls_back_snapshot_and_batch(monkeypatch, repositories):
    from storage.repository import tracking_transaction
    from analysis.prediction_tracking import save_snapshot, save_prediction_batch
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE17_TEST_DATABASE_URL'])
    snapshot_id = 'phase19a-atomic-snapshot'
    with pytest.raises(ValueError, match='complete XI'):
        with tracking_transaction(repositories[1].engine):
            save_snapshot(96, [{'id': 1}], [], [], {}, snapshot_id=snapshot_id)
            save_prediction_batch(snapshot_id, [{'week': 96, 'model': 'broken',
                'risk_profile': 'test', 'starting_xi': [], 'bench': []}])
    assert repositories[1].get_snapshot(snapshot_id) is None
