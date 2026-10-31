from datetime import datetime, timezone

from analysis.football_data_midweek import adjustment, unstarted


def test_only_confirmed_future_fixtures():
    now = datetime(2026, 10, 31, 20, tzinfo=timezone.utc)
    matches = [
        {'kickoffAt': '2026-11-01T12:00:00Z', 'status': 'SCHEDULED', 'homeScore': None, 'awayScore': None},
        {'kickoffAt': '2026-10-31T16:00:00Z', 'status': 'SCHEDULED', 'homeScore': None, 'awayScore': None},
        {'kickoffAt': '2026-11-01T12:00:00Z', 'status': 'LIVE', 'homeScore': None, 'awayScore': None},
        {'kickoffAt': '2026-11-01T12:00:00Z', 'status': 'FT', 'homeScore': 1, 'awayScore': 0},
    ]
    assert unstarted(matches, now) == matches[:1]


def test_sensitivity_is_bounded_and_missing_stays_neutral():
    features = {'1': {'xg_for': 2.0, 'goals_conceded': 1.0},
                '2': {'xg_for': 0.5, 'xg_against': 2.0,
                      'goals_scored': 0.5, 'goals_conceded': 2.0}}
    assert adjustment(features, '1', '2', 0)[0] == 0
    assert 0 < adjustment(features, '1', '2', .05)[0] < adjustment(features, '1', '2', .10)[0] <= .15
    assert adjustment(features, 'missing', '2', .10)[0] == 0
