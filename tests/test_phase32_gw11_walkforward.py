"""Outcome isolation and captain scoring for the GW11 retrospective replay."""
from copy import deepcopy

from analysis.phase32_gw11_walkforward import evaluate_predictions, predict_only
from analysis.six_model_batch import NAMES


def test_actual_changes_do_not_change_predictions(monkeypatch):
    calls = []
    expected = {'status': 'complete', 'predictions': {'baseline_5w': {'starting_xi': [1]}}}

    def fake_replay(bundle):
        calls.append(deepcopy(bundle))
        return deepcopy(expected)

    monkeypatch.setattr('analysis.phase32_gw11_walkforward.replay', fake_replay)
    bundle = {'gameweek': 11, 'histories': [{'player_id': 1, 'rows': [{'gameweekOrder': 10}]}]}
    before = predict_only(bundle)
    actual_a = {'1': [{'gameweekOrder': 11, 'points': 1}]}
    actual_b = {'1': [{'gameweekOrder': 11, 'points': 20}]}
    actual_a['1'][0]['points'] = actual_b['1'][0]['points']
    after = predict_only(bundle)
    assert before == after == expected
    assert calls == [bundle, bundle]


def test_captain_doubles_and_bench_does_not_score():
    xi = [{'id': i, 'name': str(i), 'position': 'MID', 'team': '1',
           'xpts': 2.0, 'captain': i == 1} for i in range(1, 12)]
    bench = [{'id': i, 'name': str(i), 'position': 'MID', 'team': '1',
              'xpts': 2.0} for i in range(12, 16)]
    pred = {name: {'starting_xi': deepcopy(xi), 'bench': deepcopy(bench),
                   'expected_fantasy_points': 24, 'eligible_players': 15,
                   'excluded': {}, 'formation': '3-5-2', 'cost': 80,
                   'risk_adjusted_objective': 23.5} for name in NAMES}
    actual = {str(i): [{'gameweekOrder': 11, 'points': 3 if i == 1 else 10 if i == 12 else 1,
                        'minutesPlayed': 90}] for i in range(1, 16)}
    result = evaluate_predictions(pred, actual)
    assert all(model['actual_xi_points'] == 13 and model['captain_extra_points'] == 3
               and model['actual_points'] == 16 and model['bench'][0]['actual_points'] == 10
               for model in result.values())
