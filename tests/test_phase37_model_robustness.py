"""Exact XI/captain attribution and robustness arithmetic."""
from analysis.phase37_model_robustness import attribution


def squad(players, captain, captain_points):
    return {'xi_players':[{'id':i,'name':str(i),'predicted':float(a),'actual':a} for i,a in players],
            'captain_id':captain,'captain_actual':captain_points,
            'actual_squad_points':sum(a for _,a in players)+captain_points}


def test_player_and_captain_deltas_reconcile():
    base=squad([(1,4),(2,3)]+[(i,0) for i in range(3,12)],1,4)
    exp=squad([(1,4),(12,6)]+[(i,0) for i in range(3,12)],12,6)
    result=attribution(base,exp)
    assert result['xi_actual_delta']==3
    assert result['captain_actual_delta']==2
    assert result['total_actual_delta']==5
    assert len(result['shared_ids'])==10


def test_inconsistent_total_rejected():
    base=squad([(i,1) for i in range(1,12)],1,1)
    exp=squad([(i,1) for i in range(1,12)],1,1)
    exp['actual_squad_points']+=1
    try:
        attribution(base,exp)
    except AssertionError:
        pass
    else:
        raise AssertionError('Inconsistent recorded score was accepted')
