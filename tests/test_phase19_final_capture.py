"""End-to-end prospective capture in an isolated restored PostgreSQL database."""
import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select


def test_future_week_production_and_phase15_capture(monkeypatch):
    url = os.getenv('PHASE19_CAPTURE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('PHASE19_CAPTURE_TEST_DATABASE_URL required')
    if not url.endswith('/fantasy_league_phase19_capture_test'):
        pytest.fail('Dedicated restored Phase 19 capture database required')

    from analysis import prospective_monitor
    from analysis.experimental_forecasting import NAME, BLEND
    from analysis.live_benchmark import FIXTURE_ENDPOINT
    from data_sources.tff_official import BASE
    from storage.runtime_repository import RuntimeRepository
    from storage.repository import TrackingRepository
    from storage import models as m

    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', url)
    engine = create_engine(url, pool_pre_ping=True)
    repository = RuntimeRepository(engine)
    tracking = TrackingRepository(engine)
    original = Path('historical_data/prediction_tracking.sqlite3')
    original_digest = hashlib.sha256(original.read_bytes()).hexdigest()
    now = datetime.now(timezone.utc)
    deadline = (now + timedelta(days=1)).isoformat()
    matches = [dict(item, status='SCHEDULED', homeScore=None, awayScore=None,
                    kickoffAt=(now + timedelta(days=2)).isoformat())
               for item in repository.fixture_archive()['weeks']['11']['matches']]
    archive = {'source_endpoint': FIXTURE_ENDPOINT, 'source_url': BASE + FIXTURE_ENDPOINT,
               'captured_utc': now.isoformat(),
               'weeks': {'11': {'gameweek_id': 110001, 'deadline': deadline,
                                'matches': matches}}}
    players = repository.current_player_pool()
    histories = repository.historical_records(before_week=11)
    records = [(player, histories.get(str(player['id']), [])) for player in players]

    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes

    def no_historical_file_read(path, *args, **kwargs):
        if 'historical_data' in Path(path).parts:
            raise AssertionError(f'Persistent file read in PostgreSQL capture: {path}')
        return original_read_text(path, *args, **kwargs)

    def no_historical_file_bytes(path, *args, **kwargs):
        if 'historical_data' in Path(path).parts:
            raise AssertionError(f'Persistent file read in PostgreSQL capture: {path}')
        return original_read_bytes(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', no_historical_file_read)
    monkeypatch.setattr(Path, 'read_bytes', no_historical_file_bytes)
    try:
        first = prospective_monitor.capture(fixture_archive=archive, now=now,
            players_provider=lambda: {'players': players},
            records_provider=lambda: records, include_phase15=True)
        assert first['status'] == 'captured'
        assert first['experimental_phase15']['status'] == 'saved'
        assert set(first['experimental_phase15']['model_names']) == {NAME, BLEND}
        snapshot_id = first['snapshot_id']
        saved = [tracking.get_prediction(pid) for pid in tracking.prediction_ids(snapshot_id)]
        assert len(saved) == first['predictions_created'] + 2
        assert all(item['gameweek'] == 11 for item in saved)
        repeated = prospective_monitor.capture(fixture_archive=archive, now=now,
            players_provider=lambda: pytest.fail('Repeated capture fetched players'),
            include_phase15=True)
        assert repeated['status'] == 'already_captured'
        assert repeated['snapshot_id'] == snapshot_id
        assert len(tracking.prediction_ids(snapshot_id)) == len(saved)
    finally:
        monkeypatch.setattr(Path, 'read_text', original_read_text)
        monkeypatch.setattr(Path, 'read_bytes', original_read_bytes)
        engine.dispose()
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_digest


def test_restored_postgres_flask_content_and_failure_paths(monkeypatch):
    url = os.getenv('PHASE19_CAPTURE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('PHASE19_CAPTURE_TEST_DATABASE_URL required')
    if not url.endswith('/fantasy_league_phase19_capture_test'):
        pytest.fail('Dedicated restored Phase 19 capture database required')
    from app import create_app

    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', url)
    client = create_app().test_client()
    for path, marker in (('/', b'Dashboard'), ('/lineup', b'lineup'),
                         ('/benchmark', b'benchmark'), ('/tools', b'Legacy Tools')):
        response = client.get(path)
        assert response.status_code == 200, (path, response.get_json(silent=True))
        assert marker.lower() in response.data.lower()
    players = client.get('/api/players/tff')
    assert players.status_code == 200 and players.get_json()['count'] == 572
    benchmark = client.get('/api/benchmark/report')
    assert benchmark.status_code == 200 and len(benchmark.get_json()['predictions']) >= 11
    prospective = client.get('/api/prospective/report')
    assert prospective.status_code == 200 and 'by_model' in prospective.get_json()
    accuracy = client.get('/api/benchmark/player-accuracy')
    assert accuracy.status_code == 200 and 'by_gameweek' in accuracy.get_json()
    history = client.get('/api/history/latest-round')
    assert history.status_code == 200 and 'players' in history.get_json()

    monkeypatch.setattr('storage.db.engine_from_env',
                        lambda: (_ for _ in ()).throw(RuntimeError('PostgreSQL unavailable')))
    for path in ('/', '/benchmark', '/tools', '/api/players/tff',
                 '/api/benchmark/report?saved=1', '/api/dashboard/latest?week=11'):
        response = client.get(path)
        assert response.status_code == 503, (path, response.status_code)


def test_postgres_tools_api_content(monkeypatch):
    url = os.getenv('PHASE19_CAPTURE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('PHASE19_CAPTURE_TEST_DATABASE_URL required')
    if not url.endswith('/fantasy_league_phase19_capture_test'):
        pytest.fail('Dedicated restored Phase 19 capture database required')
    import importlib
    from io import BytesIO
    from app import create_app

    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL', url)
    app_module = importlib.import_module('app')
    monkeypatch.setattr(app_module, 'fetch_players', lambda: {
        'players': [{'name': 'External synthetic', 'team': 'A'}], 'count': 1})
    monkeypatch.setattr(app_module, 'free_sync', lambda: {
        'fixtures': [{'team': 'A', 'opponent': 'B', 'fdr': 3}],
        'team_matches': {'a': 9}, 'matches_loaded': 9})
    monkeypatch.setattr(app_module, 'sync', lambda *args, **kwargs: {
        'fixtures': [{'team': 'A'}], 'matches_loaded': 1})
    client = create_app().test_client()
    assert client.get('/api/players/xgedge').get_json()['count'] == 1
    assert client.get('/api/free/refresh').get_json()['matches_loaded'] == 9
    assert client.get('/api/live/refresh').get_json()['matches_loaded'] == 1
    projected = client.post('/api/projections/next-week', json={
        'players': [], 'fixtures': [], 'team_matches': {}})
    assert projected.status_code == 200 and projected.get_json()['projected'] == 0
    availability = client.post('/api/availability/check', json={
        'players': [{'id': 1, 'availability': 'AVAILABLE'}], 'overrides': [], 'round': 11})
    assert availability.status_code == 200 and '1' in availability.get_json()['decisions']
    imported = client.post('/api/players/import', data={
        'stats': (BytesIO(b'Player,Club,Min,G,A,xG,xA\nP,A,90,1,0,0.3,0.1\n'), 'stats.csv')})
    assert imported.status_code == 200 and imported.get_json()['count'] == 1
    predicted = client.post('/api/players/predict', data={
        'players': (BytesIO(b'name,team,position,price,minutes_last5,goals_last5,assists_last5\nP,A,MID,4,450,1,0\n'), 'players.csv')})
    assert predicted.status_code == 200 and predicted.get_json()['count'] == 1
    for path, key in (('/api/benchmark/recovered-history', 'position_evidence'),
                      ('/api/benchmark/recovered-models', 'source_policy'),
                      ('/api/benchmark/player-ranking?source=official', 'source_policy')):
        response = client.get(path)
        assert response.status_code == 200 and key in response.get_json(), path


def test_staged_reports_and_model_metadata_import_idempotently():
    url = os.getenv('PHASE19_CAPTURE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('PHASE19_CAPTURE_TEST_DATABASE_URL required')
    if not url.endswith('/fantasy_league_phase19_capture_test'):
        pytest.fail('Dedicated restored Phase 19 capture database required')
    from sqlalchemy import func
    from storage.import_runtime_metadata import import_runtime_metadata
    from storage import models as m

    engine = create_engine(url)
    first = import_runtime_metadata(engine)
    second = import_runtime_metadata(engine)
    assert first['reports']['inserted'] + first['reports']['skipped'] >= 23
    assert first['models']['inserted'] + first['models']['skipped'] >= 7
    assert second['reports']['inserted'] == second['models']['inserted'] == 0
    with engine.connect() as db:
        assert db.execute(select(func.count()).select_from(m.historical_reports)).scalar_one() >= 23
        assert db.execute(select(func.count()).select_from(m.forecast_models)).scalar_one() >= 7
    engine.dispose()
