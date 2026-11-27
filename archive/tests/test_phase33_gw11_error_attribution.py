"""Exact GW11 score-gap accounting from player and captain contributions."""
import pytest

from archive.analysis.phase33_gw11_error_attribution import pair_attribution, unique_errors


def model(players, captain):
    xi = [{'id': pid, 'name': str(pid), 'position': 'MID', 'predicted_xpts': pred,
           'actual_points': actual, 'difference': pred-actual, 'actual_minutes': 90}
          for pid,pred,actual in players]
    captain_points = next(p['actual_points'] for p in xi if p['id'] == captain)
    return {'starting_xi': xi, 'bench': [], 'actual_xi_points': sum(p['actual_points'] for p in xi),
            'captain_extra_points': captain_points,
            'actual_points': sum(p['actual_points'] for p in xi) + captain_points}


def test_pair_attribution_reconciles_xi_and_captain():
    a = model([(1,5,4),(2,6,10),(3,4,0)], 2)
    b = model([(1,7,4),(4,3,2),(5,4,3)], 4)
    result = pair_attribution(a,b)
    assert [p['id'] for p in result['shared']] == [1]
    assert result['a_only_actual'] == 10
    assert result['b_only_actual'] == 5
    assert result['xi_delta'] == 5
    assert result['captain_delta'] == 8
    assert result['substitution_delta'] == 0
    assert result['total_delta'] == 13 == a['actual_points'] - b['actual_points']


def test_mismatched_recorded_total_fails():
    a = model([(1,5,4)],1)
    b = model([(2,5,3)],2)
    a['actual_points'] += 1
    with pytest.raises(AssertionError):
        pair_attribution(a,b)


def test_unique_errors_keep_one_observation_per_player():
    a = model([(1,6,0),(2,1,5)],1)
    b = model([(1,7,0),(3,1,6)],1)
    over = unique_errors({'a':a,'b':b},'over')
    under = unique_errors({'a':a,'b':b},'under')
    assert [(p['id'],p['difference']) for p in over] == [(1,7)]
    assert [p['id'] for p in under] == [3,2]
