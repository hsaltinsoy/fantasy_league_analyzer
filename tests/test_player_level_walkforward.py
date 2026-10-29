import json

import pytest

from analysis.player_level_walkforward import (audit, baseline_predictions, evaluate,
    save_report, valid_row)


def fixture_store(tmp_path):
    store = tmp_path / 'archive'
    store.mkdir()
    weeks = {}
    for week in range(1, 4):
        weeks[str(week)] = {'gameweek_id': week, 'matches': [{'id': week,
            'homeClubId': 1, 'awayClubId': 2, 'status': 'FT',
            'homeScore': 1, 'awayScore': 0}]}
    (store/'tff_fixtures_verified_v5.json').write_text(json.dumps({'weeks': weeks}), encoding='utf-8')
    # This current catalog must never become a historical position source.
    (store/'players.json').write_text(json.dumps([{'id': 1, 'position': 'FWD'}]), encoding='utf-8')
    rows = [{'gameweekOrder': week, 'gameweekId': week, 'points': points,
             'played': played, 'minutesPlayed': 90 if played else 0,
             'opponentClubId': 2, 'homeAway': 'H'}
            for week, points, played in ((1, 2, True), (2, 0, True), (3, 0, False))]
    (store/'player_1.json').write_text(json.dumps(rows), encoding='utf-8')
    return store, rows, weeks


def test_future_and_target_week_points_rejected_as_features():
    past = [{'gameweekOrder': 1, 'points': 2}, {'gameweekOrder': 2, 'points': 4}]
    assert baseline_predictions(past, 3) == {'recent_3_average': 3, 'season_to_date_average': 3}
    with pytest.raises(ValueError, match='future data'):
        baseline_predictions(past + [{'gameweekOrder': 3, 'points': 100}], 3)
    with pytest.raises(ValueError, match='future data'):
        baseline_predictions(past + [{'gameweekOrder': 4, 'points': 100}], 3)


def test_zero_point_appearance_and_explicit_nonappearance_are_distinct(tmp_path):
    store, _, _ = fixture_store(tmp_path)
    coverage = audit(store)
    gw2, gw3 = coverage['weeks'][:2]
    assert gw2['zero_point_appearances'] == 1 and gw2['appearances'] == 1
    assert gw3['explicit_nonappearances'] == 1 and gw3['appearances'] == 0
    report = evaluate(store)
    recent = report['cumulative']['recent_3_average']
    assert recent['unconditional']['n'] == 2
    assert recent['appearance']['n'] == 1
    assert all(report['cumulative'][name]['status'] == 'not_evaluable'
               for name in ('short_form_3w', 'baseline_5w', 'conservative_5w',
                            'robust_5w', 'stable_8w'))


def test_missing_result_is_not_scored_as_zero(tmp_path):
    store, rows, _ = fixture_store(tmp_path)
    (store/'player_1.json').write_text(json.dumps(rows[:2]), encoding='utf-8')
    report = evaluate(store)
    assert report['data_audit']['weeks'][1]['missing_target_rows'] == 1
    assert report['by_gameweek'][1]['baselines']['recent_3_average']['unconditional']['n'] == 0
    assert report['cumulative']['recent_3_average']['unconditional']['n'] == 1


def test_incorrect_fixture_mapping_and_incomplete_results_rejected(tmp_path):
    store, rows, weeks = fixture_store(tmp_path)
    bad = dict(rows[1], opponentClubId=99)
    assert valid_row(bad, 2, weeks['2'])[1] == 'incorrect_fixture_mapping'
    bad = dict(rows[1], points=None)
    assert valid_row(bad, 2, weeks['2'])[1] == 'missing_or_inconsistent_result'
    bad = dict(rows[1], played=False)
    assert valid_row(bad, 2, weeks['2'])[1] == 'appearance_minutes_inconsistent'
    weeks['2']['matches'][0]['status'] = 'SCHEDULED'
    (store/'tff_fixtures_verified_v5.json').write_text(json.dumps({'weeks': weeks}), encoding='utf-8')
    report = evaluate(store)
    assert report['by_gameweek'][0]['baselines']['recent_3_average']['unconditional']['n'] == 0


def test_matched_samples_bias_and_export(tmp_path):
    store, _, _ = fixture_store(tmp_path)
    report = evaluate(store)
    for week in report['by_gameweek']:
        assert (week['baselines']['recent_3_average']['unconditional']['n'] ==
                week['baselines']['season_to_date_average']['unconditional']['n'])
    assert report['cumulative']['recent_3_average']['unconditional']['bias'] > 0
    assert report['cumulative']['recent_3_average']['unconditional']['mae'] is not None
    paths = save_report(report, tmp_path/'output')
    assert [p.name for p in paths] == ['player_level_comparison.csv',
                                      'player_level_cumulative.csv', 'player_level_report.json']
    assert all(p.exists() for p in paths)
    assert 'historical_position_unavailable' in paths[1].read_text(encoding='utf-8')


def test_dashboard_labels_retrospective_and_missing_metrics(monkeypatch):
    from app import create_app
    from analysis import live_benchmark
    monkeypatch.setattr(live_benchmark, 'report', lambda **kwargs: {
        'predictions': [], 'evaluation_runs': [], 'by_model': {},
        'counts': {'verified': 0, 'unverified': 0, 'complete_evaluations': 0,
                   'locally_recorded_pre_deadline': 0, 'post_deadline': 0}})
    client = create_app().test_client()
    response = client.get('/benchmark')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Player Forecast Accuracy' in html
    assert 'Retrospective reconstruction' in html
    assert 'historical_position_unavailable' in html
    assert 'season to date average' in html
    report_response = client.get('/api/benchmark/player-accuracy')
    assert report_response.status_code == 200
    assert report_response.json['classification'] == 'retrospective_player_level_only'
