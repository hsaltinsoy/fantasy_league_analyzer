import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from app import create_app
from app.dashboard_view import dashboard_data, next_gameweek


GW10_SNAPSHOT = '1e9f5094-9b24-42f6-a0ff-ddf201685aa8'


def _original_gw10_digest(path):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
        rows = db.execute('SELECT * FROM predictions WHERE snapshot_id=? ORDER BY id',
                          (GW10_SNAPSHOT,)).fetchall()
    return len(rows), hashlib.sha256(repr(rows).encode()).hexdigest()


def test_dashboard_and_existing_pages_render_without_mutating_original_gw10():
    path = 'historical_data/prediction_tracking.sqlite3'
    before = _original_gw10_digest(path)
    client = create_app().test_client()
    for route in ('/', '/lineup', '/benchmark', '/tools'):
        response = client.get(route)
        assert response.status_code == 200
        for destination in ('/', '/lineup', '/benchmark', '/tools'):
            assert f'href="{destination}"'.encode() in response.data
    assert before == _original_gw10_digest(path)
    assert before[0] == 11


def test_dashboard_uses_production_api_and_shows_saved_squad():
    client = create_app().test_client()
    page = client.get('/').get_data(as_text=True)
    assert 'Dashboard v2.0' in page
    assert 'fetch(\'/api/lineup/generate?' in page
    assert 'Starting XI' in page
    assert 'Bench' in page
    assert 'Snapshot' in page
    assert 'Fixture coverage' in page
    assert 'Model Comparison' in page
    assert 'Risk Analysis' in page
    assert 'Historical Analysis' in page
    assert 'Live Benchmark' in page
    assert 'Optimizer v1.9' not in page
    assert 'verified live performance' not in page
    assert client.get('/api/lineup/latest?week=10').status_code == 200
    assert client.get('/api/lineup/generate?week=1').status_code == 400


def test_upcoming_week_is_from_fixture_deadline_not_hard_coded(tmp_path):
    fixture = {'source_endpoint': 'official-fixtures', 'captured_utc': '2026-10-29T10:00:00Z',
               'weeks': {'10': {'gameweek_id': 1010, 'deadline': '2026-10-30T16:00:00Z',
                                'matches': [{'id': 1}]},
                         '11': {'gameweek_id': 1011, 'deadline': '2026-11-06T16:00:00Z',
                                'matches': [{'id': 2}]}}}
    (tmp_path/'tff_fixtures_verified_v5.json').write_text(json.dumps(fixture), encoding='utf-8')
    assert next_gameweek(tmp_path, datetime(2026, 10, 29, tzinfo=timezone.utc))['number'] == 10
    assert next_gameweek(tmp_path, datetime(2026, 10, 31, tzinfo=timezone.utc))['number'] == 11
    assert next_gameweek(tmp_path, datetime(2026, 11, 7, tzinfo=timezone.utc)) is None


def test_missing_lineup_and_tracking_are_explicit(tmp_path):
    (tmp_path/'tff_fixtures_verified_v5.json').write_text(json.dumps({
        'weeks': {'10': {'gameweek_id': 10, 'deadline': '2026-10-30T16:00:00Z',
                         'matches': [{'id': 1}]}}}), encoding='utf-8')
    now = datetime(2026, 10, 29, tzinfo=timezone.utc)
    assert dashboard_data(tmp_path, now=now, prediction_path=tmp_path/'absent.db')['lineup'] is None
    (tmp_path/'next_week_gw10.json').write_text(json.dumps({
        'week': 10, 'starting_xi': [{'id': i} for i in range(11)],
        'prediction_tracking': {'id': 'missing', 'snapshot_id': 'missing'}}), encoding='utf-8')
    data = dashboard_data(tmp_path, now=now, prediction_path=tmp_path/'absent.db')
    assert data['lineup'] is not None
    assert data['prediction'] is None
    assert not (tmp_path/'absent.db').exists()


def test_responsive_dashboard_styles_and_legacy_actions_remain():
    from pathlib import Path
    css = Path('app/static/dashboard.css').read_text(encoding='utf-8')
    assert '@media(max-width:760px)' in css
    assert '@media(max-width:480px)' in css
    legacy = create_app().test_client().get('/tools').get_data(as_text=True)
    assert 'id="refresh-live"' in legacy
    assert 'id="optimize-squad"' in legacy
    assert 'id="save-backtest"' in legacy
