"""Phase 19C parity checks against staged PostgreSQL evidence."""
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine


@pytest.fixture(scope='module')
def history_engine():
    url = os.getenv('PHASE18_TEST_DATABASE_URL')
    if not url:
        pytest.skip('PHASE18_TEST_DATABASE_URL required')
    if not url.endswith('/fantasy_league_phase18_test2'):
        pytest.fail('Dedicated Phase 18 test database required')
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


def test_team_of_week_staged_evidence_matches_file(history_engine):
    from storage.runtime_repository import RuntimeRepository
    from analysis.team_of_week_v36 import load
    expected = load('historical_data/team_of_week_verified.json')
    actual = RuntimeRepository(history_engine).team_of_week()
    assert actual == expected
    assert len(actual) == 9 and sum(map(len, actual.values())) == 99


def test_phase15_training_parity_with_chronological_gap(monkeypatch, history_engine):
    from analysis.experimental_prospective import train_for_target
    monkeypatch.setenv('STORAGE_BACKEND', 'sqlite')
    legacy_model, legacy_evidence = train_for_target(11)
    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE18_TEST_DATABASE_URL'])
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    model, evidence = train_for_target(11)
    assert model == legacy_model and evidence == legacy_evidence
    assert evidence['training_weeks'] == [4, 5, 6, 7, 8, 9]
    assert evidence['training_n'] == 2438


def test_postgres_identity_crosswalk_does_not_promote_reviews(monkeypatch, history_engine):
    from data_sources.identity import load_crosswalk
    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE18_TEST_DATABASE_URL'])
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    assert load_crosswalk()['entries'] == []


def test_verified_identity_revision_stays_in_postgres(monkeypatch, history_engine):
    from data_sources.identity import add_verified_identity, load_crosswalk
    from storage.runtime_repository import RuntimeRepository
    from storage import models as m
    from sqlalchemy import select

    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE18_TEST_DATABASE_URL'])
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    with history_engine.connect() as db:
        player_id = db.execute(select(m.players.c.id).order_by(m.players.c.id).limit(1)).scalar_one()
    original = Path('historical_data/player_identity_crosswalk.json')
    digest = original.read_bytes() if original.exists() else None
    url = f'https://www.xg-edge.com/players/phase19-test-{player_id}'
    version = add_verified_identity(player_id, url, 'synthetic reviewed test link',
                                    aliases=['Synthetic alias'])
    entries = load_crosswalk()['entries']
    assert version and any(str(entry['tff_id']) == player_id and
                           entry['profile_url'] == url for entry in entries)
    assert (original.read_bytes() if original.exists() else None) == digest
    with pytest.raises(ValueError, match='already exists'):
        add_verified_identity(player_id, url, 'synthetic reviewed test link')


def test_dashboard_tracking_writes_only_postgres(monkeypatch):
    from app import create_app
    import hashlib
    url = os.getenv('PHASE17_TEST_DATABASE_URL')
    if not url:
        pytest.skip('PHASE17_TEST_DATABASE_URL required')
    if not url.endswith('/fantasy_league_phase17_test'):
        pytest.fail('Dedicated Phase 17 test database required')
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    source = Path('historical_data/prediction_tracking.sqlite3')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    players = [{'id': i, 'name': f'P{i}', 'xpts': 2, 'position': 'MID',
                'price': 4, 'team': '1'} for i in range(30001, 30016)]
    solution = {'starting_xi': players[:11], 'squad': players,
                'captain': players[0], 'expected_points': 24,
                'formation': '4-4-2', 'squad_cost': 60}
    response = create_app().test_client().post('/api/dashboard/track', json={
        'week': 30, 'solution': solution, 'players': players, 'fixtures': []})
    assert response.status_code == 200
    assert response.get_json()['snapshot_id']
    client = create_app().test_client()
    latest = client.get('/api/dashboard/latest?week=30')
    assert latest.status_code == 200
    assert latest.get_json()['lineup']['prediction_tracking']['id'] == response.get_json()['id']
    evaluated = client.post('/api/dashboard/backtest/evaluate', json={
        'week': 30,
        'actual_players': [{'id': player['id'], 'round_points': 3} for player in players]})
    assert evaluated.status_code == 200
    assert evaluated.get_json()['status'] == 'complete'
    assert evaluated.get_json()['report_id']
    assert evaluated.get_json()['source_provenance'] == 'browser_confirmed_round_points_not_independently_verified'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_phase15_failure_rolls_back_production_capture(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import create_engine, select
    from storage import models as m
    from analysis import live_benchmark, prospective_monitor
    from analysis.prediction_tracking import save_snapshot
    from data_sources.tff_official import BASE

    url = os.environ['PHASE17_TEST_DATABASE_URL']
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    now = datetime(2099, 1, 1, tzinfo=timezone.utc)
    deadline = (now + timedelta(days=1)).isoformat()
    monkeypatch.setattr('analysis.prediction_tracking.utc_now', lambda: now.isoformat())
    archive = {'source_endpoint': live_benchmark.FIXTURE_ENDPOINT,
               'source_url': BASE + live_benchmark.FIXTURE_ENDPOINT,
               'captured_utc': now.isoformat(),
               'weeks': {'94': {'gameweek_id': 94001, 'deadline': deadline,
                                'matches': [{'id': 94001, 'status': 'SCHEDULED',
                                             'kickoffAt': (now + timedelta(days=2)).isoformat()}]}}}
    snapshot_id = 'phase19d-rollback-phase15'

    def production(**kwargs):
        save_snapshot(94, [{'id': 94001}], [], [], {'official_gameweek_id': 94001},
                      snapshot_id=snapshot_id, deadline_at=deadline,
                      deadline_source=archive['source_url'], require_pre_deadline=True)
        return {'snapshot': {'id': snapshot_id}, 'predictions': [],
                'data_quality': {}, 'variants': {}}

    monkeypatch.setattr(live_benchmark, 'generate', production)
    monkeypatch.setattr('analysis.experimental_prospective.save_variants',
                        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('phase15 failed')))
    with pytest.raises(ValueError, match='phase15 failed'):
        prospective_monitor.capture(fixture_archive=archive, now=now,
            players_provider=lambda: {'players': [{'id': 94001}]},
            records_provider=lambda: [], include_phase15=True)
    engine = create_engine(url)
    with engine.connect() as db:
        assert db.execute(select(m.snapshots.c.id).where(m.snapshots.c.id == snapshot_id)).first() is None
    engine.dispose()


def test_generated_benchmark_report_is_idempotent_and_retrievable(monkeypatch, history_engine):
    from app import create_app
    from storage.runtime_repository import RuntimeRepository

    monkeypatch.setenv('DATABASE_URL', os.environ['PHASE18_TEST_DATABASE_URL'])
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    repository = RuntimeRepository(history_engine)
    content = {'predictions': [{'id': 'synthetic-report-row'}], 'source': 'test'}
    first = repository.save_generated_report('phase19-test', content)
    assert repository.save_generated_report('phase19-test', content) == first
    saved = repository.latest_generated_report('phase19-test')
    assert saved['content'] == content
    assert saved['evidence_quality'] == 'generated_from_postgres_runtime'
    client = create_app().test_client()
    response = client.post('/api/benchmark/report/save')
    assert response.status_code == 200
    retrieved = client.get('/api/benchmark/report?saved=1')
    assert retrieved.status_code == 200
    assert retrieved.get_json()['id'] == response.get_json()['id']
    assert retrieved.get_json()['content']['predictions'] == client.get('/api/benchmark/report').get_json()['predictions']


def test_generated_report_failure_has_no_file_fallback(monkeypatch):
    from app import create_app

    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setattr('storage.db.engine_from_env',
                        lambda: (_ for _ in ()).throw(RuntimeError('PostgreSQL unavailable')))
    client = create_app().test_client()
    assert client.get('/api/benchmark/report?saved=1').status_code == 503
    assert client.post('/api/benchmark/report/save').status_code == 503


def test_postgres_rejects_custom_sqlite_tracking_path(monkeypatch, tmp_path):
    from analysis.prediction_tracking import get_snapshot

    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    with pytest.raises(ValueError, match='Custom SQLite tracking paths'):
        get_snapshot('missing', path=tmp_path / 'tracking.sqlite3')
    assert not (tmp_path / 'tracking.sqlite3').exists()


def test_postgres_is_default_tracking_backend(monkeypatch):
    from analysis.prediction_tracking import _postgres, DEFAULT_DB
    from storage.repository import TrackingRepository

    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    monkeypatch.setenv('DATABASE_URL',
        'postgresql+psycopg://test:test@127.0.0.1:5433/isolated_no_connection')
    repository = _postgres(DEFAULT_DB)
    assert isinstance(repository, TrackingRepository)
    repository.engine.dispose()
