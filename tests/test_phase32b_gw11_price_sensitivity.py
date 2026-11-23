"""Price-only scenario construction and outcome isolation."""
from copy import deepcopy

from analysis.phase32b_gw11_price_sensitivity import generate_all, price_scenarios


def test_price_scenarios_only_change_price_and_use_fallback():
    players = [{'id': 1, 'name': 'One', 'price': 8.0, 'position': 'MID', 'club_id': 1},
               {'id': 2, 'name': 'Two', 'price': 5.0, 'position': 'DEF', 'club_id': 2}]
    histories = [{'player_id': 1, 'rows': [{'gameweekOrder': 9, 'cost': 7.5},
                                          {'gameweekOrder': 10, 'cost': 7.0}]},
                 {'player_id': 2, 'rows': [{'gameweekOrder': 9, 'cost': 0},
                                          {'gameweekOrder': 10, 'cost': None}]}]
    base = {'players': players, 'histories': histories, 'fixtures': [{'homeClubId': 1}],
            'external_matches': [{'id': 1}]}
    before = deepcopy(base)
    scenarios = price_scenarios(base)
    assert base == before
    assert [p['price'] for p in scenarios['snapshot_oct31']['bundle']['players']] == [8.0, 5.0]
    assert [p['price'] for p in scenarios['gw9_postmatch']['bundle']['players']] == [7.5, 5.0]
    assert [p['price'] for p in scenarios['gw10_postmatch']['bundle']['players']] == [7.0, 5.0]
    assert scenarios['gw10_postmatch']['fallback_ids'] == [2]
    assert all(item['bundle']['histories'] == histories for item in scenarios.values())


def test_generation_receives_no_actual_results():
    scenarios = {'a': {'bundle': {'players': [{'price': 8}], 'histories': []}}}
    observed = []
    def predictor(bundle):
        observed.append(deepcopy(bundle))
        return {'predictions': {'lineup': [1]}}
    first = generate_all(scenarios, predictor=predictor)
    actuals = {'1': {'points': 1}}
    actuals['1']['points'] = 99
    second = generate_all(scenarios, predictor=predictor)
    assert first == second
    assert observed == [scenarios['a']['bundle'], scenarios['a']['bundle']]
