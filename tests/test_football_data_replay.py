import os

import pytest
from sqlalchemy import create_engine

from analysis.football_data_replay import run


def test_frozen_replay_without_live_api(monkeypatch):
    url = os.getenv('PHASE20_REPLAY_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Dedicated replay test database required')
    if not url.endswith('/fantasy_league_phase20_replay_test'):
        pytest.fail('Refusing non-isolated replay database')
    monkeypatch.setattr('analysis.live_benchmark.fetch_official_fixtures',
                        lambda: pytest.fail('Live fixture API used by replay'))
    engine = create_engine(url, pool_pre_ping=True)
    try:
        report = run(engine)
        assert report['reproduction'] == 'passed'
        assert report['eligible_players'] == 179
        assert [report['scenarios'][key]['expected_points'] for key in
                ('baseline', 'small', 'medium', 'large')] == [67.92, 68.34, 68.79, 69.34]
    finally:
        engine.dispose()
