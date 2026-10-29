import pytest
from analysis.backtesting import evaluate_snapshot

def test_evaluation_captain_and_missing():
    snapshot={'round':10,'pre_round_confirmed':True,'starting_xi':list(range(1,12)), 'captain_id':1,'predictions':{str(i):2 for i in range(1,12)}}
    actual=[{'id':i,'round_points':3} for i in range(1,12)]
    result=evaluate_snapshot(snapshot,actual,10)
    assert result['predicted_total']==24
    assert result['actual_total']==36
    assert result['difference']==12
    assert evaluate_snapshot(snapshot,actual[:-1],10)['status']=='incomplete'
    with pytest.raises(ValueError): evaluate_snapshot(snapshot,actual,9)
    snapshot['pre_round_confirmed']=False
    with pytest.raises(ValueError): evaluate_snapshot(snapshot,actual,10)
