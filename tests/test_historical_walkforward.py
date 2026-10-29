import copy
import json

import pytest

from analysis.historical_walkforward import _strict_inputs, audit_coverage, evaluate_week, run, save_report
from analysis.benchmark_evaluation import FIXTURE_ENDPOINT, FIXTURE_URL, PLAYER_HISTORY_URL


def evidence(week=5):
    fixtures = [{'id': i, 'homeClubId': 2*i-1, 'awayClubId': 2*i,
                 'status': 'SCHEDULED'} for i in range(1, 4)]
    players = []
    histories = []
    positions = ['GK']*2 + ['DEF']*5 + ['MID']*5 + ['FWD']*3
    for pid, position in enumerate(positions, 1):
        club = (pid-1) % 6 + 1
        players.append({'id': pid, 'name': f'P{pid}', 'club_id': club,
                        'team': str(club), 'position': position,
                        'price': 5., 'availability': 'AVAILABLE'})
        histories.append({'player_id': pid, 'rows': [{'gameweekOrder': week-1,
                            'points': 2., 'minutesPlayed': 90, 'cost': 5.}]})
    snapshot = {'id': 'historical-test', 'gameweek': week,
                'classification': 'historical_reconstruction',
                'captured_at': '2026-09-01T12:00:00Z',
                'deadline_at': '2026-09-02T12:00:00Z',
                'source': {'official_gameweek_id': 50},
                'payload': {'players': players, 'fixtures': fixtures,
                            'histories': histories, 'data_quality': {}}}
    completed = copy.deepcopy(fixtures)
    for match in completed:
        match.update(status='FT', homeScore=1, awayScore=0)
    archive = {'source_endpoint': FIXTURE_ENDPOINT, 'source_url': FIXTURE_URL,
               'captured_utc': '2026-09-03T12:00:00Z',
               'weeks': {str(week): {'gameweek_id': 50, 'matches': completed}}}
    calls = []
    def predictor(target, input_players, records, lookup, tow, *, model):
        calls.append((target, model, copy.deepcopy(records)))
        assert all(all(row['gameweekOrder'] < target for row in history)
                   for _, history in records)
        chosen = {1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14}
        xi = [dict(p, xpts=2., opponent=lookup[target][str(p['club_id'])],
                   captain=p['id']==1) for p in input_players if p['id'] in chosen]
        bench = [dict(p, xpts=2., opponent=lookup[target][str(p['club_id'])])
                 for p in input_players if p['id'] not in chosen]
        return {'starting_xi': xi, 'bench': bench,
                'formation': '4-4-2', 'cost': 75.}
    def actual_provider(target, selected):
        assert calls and target == week
        rows = {}
        for pid in selected:
            club = players[int(pid)-1]['club_id']
            rows[pid] = [{'gameweekOrder': week, 'gameweekId': 50,
                          'playerId': int(pid), 'points': 1.,
                          'opponentClubId': club+1 if club % 2 else club-1,
                          'homeAway': 'H' if club % 2 else 'A'}]
        return {'source_url': PLAYER_HISTORY_URL, 'retrieved_at': '2026-09-03T12:00:00Z',
                'rows_by_player': rows, 'provenance': 'test_official'}
    return snapshot, archive, predictor, actual_provider, calls


def test_complete_xi_captain_and_identical_frozen_inputs():
    snapshot, archive, predictor, provider, calls = evidence()
    output = evaluate_week(snapshot, archive, provider,
                           models={'short_form_3w': {}, 'baseline_5w': {}}, predictor=predictor)
    assert len(calls) == 2
    assert calls[0][2] == calls[1][2]
    assert output['classification'] == 'retrospective_reconstruction'
    for result in output['models'].values():
        assert result['status'] == 'retrospective_reconstruction'
        assert result['predicted_points'] == 24.
        assert result['starting_xi_actual_points'] == 11.
        assert result['captain_contribution'] == 1.
        assert result['actual_points'] == 12.
        assert result['player_metrics']['mae'] == 1.
        assert result['coverage'] == 1.


def test_target_or_future_statistics_in_snapshot_rejected():
    snapshot, archive, predictor, provider, _ = evidence()
    snapshot['payload']['histories'][0]['rows'].append({'gameweekOrder': 5, 'points': 99})
    with pytest.raises(ValueError, match='future_statistics'):
        evaluate_week(snapshot, archive, provider, predictor=predictor)


def test_missing_price_and_postdeadline_snapshot_rejected():
    snapshot, _, _, _, _ = evidence()
    snapshot['payload']['players'][0]['price'] = None
    with pytest.raises(ValueError, match='missing_historical_player_field'):
        _strict_inputs(snapshot, 5)
    snapshot, _, _, _, _ = evidence()
    snapshot['captured_at'] = '2026-09-03T12:00:00Z'
    with pytest.raises(ValueError, match='no_predeadline_input_capture'):
        _strict_inputs(snapshot, 5)


def test_player_transfer_and_incorrect_fixture_mapping_not_scored():
    snapshot, archive, predictor, provider, _ = evidence()
    def transferred(week, ids):
        value = provider(week, ids)
        value['rows_by_player']['1'][0]['opponentClubId'] = 6
        return value
    output = evaluate_week(snapshot, archive, transferred, models={'short_form_3w': {}}, predictor=predictor)
    assert output['models']['short_form_3w']['status'] == 'not_evaluable'
    assert output['models']['short_form_3w']['player_issues']['1'] == 'opponent_or_venue_mismatch'
    snapshot, archive, predictor, provider, _ = evidence()
    archive['weeks']['5']['matches'][0]['id'] = 999
    with pytest.raises(ValueError, match='fixture_id_or_club_mismatch'):
        evaluate_week(snapshot, archive, provider, predictor=predictor)


def test_missing_actual_is_not_zero():
    snapshot, archive, predictor, provider, _ = evidence()
    def incomplete(week, ids):
        value = provider(week, ids)
        value['rows_by_player'].pop('1')
        return value
    output = evaluate_week(snapshot, archive, incomplete, models={'short_form_3w': {}}, predictor=predictor)
    result = output['models']['short_form_3w']
    assert output['classification'] == 'not_evaluable'
    assert result['status'] == 'not_evaluable'
    assert result['reason'] == 'missing_actual_results'
    assert result['coverage'] == 10/11


def test_invalid_squad_is_not_scored():
    snapshot, archive, predictor, provider, _ = evidence()
    def invalid(*args, **kwargs):
        lineup = predictor(*args, **kwargs)
        lineup['bench'].pop()
        return lineup
    output = evaluate_week(snapshot, archive, provider, models={'short_form_3w': {}}, predictor=invalid)
    assert output['classification'] == 'not_evaluable'
    assert output['models']['short_form_3w']['reason'] == 'incomplete_starting_xi_bench_or_captain'


def test_audit_and_report_do_not_fabricate_lineups(tmp_path):
    store = tmp_path / 'archive'
    store.mkdir()
    (store / 'players.json').write_text(json.dumps([{'id': 1, 'price': 10.}]), encoding='utf-8')
    (store / 'player_1.json').write_text(json.dumps([{'gameweekOrder': 1,
         'points': 0, 'cost': 5}, {'gameweekOrder': 2, 'points': 3, 'cost': 6}]), encoding='utf-8')
    coverage = audit_coverage(store, store / 'missing_snapshots')
    assert coverage['weeks'][0]['reason'] == 'no_preseason_history'
    assert coverage['weeks'][1]['prior_positive_price_players'] == 1
    assert all(row['classification'] == 'not_evaluable' for row in coverage['weeks'])
    report = run(store, store / 'missing_snapshots')
    assert report['verified_historical_count'] == 0
    assert report['retrospective_reconstruction_count'] == 0
    assert all(m['team_metrics']['n'] == 0 for m in report['cumulative_by_model'].values())
    json_path, csv_path, cumulative_path = save_report(report, tmp_path / 'report')
    assert json_path.exists() and csv_path.exists() and cumulative_path.exists()
    assert len(csv_path.read_text(encoding='utf-8').splitlines()) == 1 + 9*9
    assert len(cumulative_path.read_text(encoding='utf-8').splitlines()) == 1 + 9
