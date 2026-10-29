from data_sources.player_csv import parse_players
from analysis.player_prediction import predict
import pytest

def test_player_prediction_with_fixture():
    p = parse_players('name,team,position,price,minutes_last5,goals_last5,assists_last5,xg_last5,xa_last5\nSample,Beşiktaş,FW D,8,400,2,1,2.2,0.8\n'.replace('FW D','FWD'))
    results = predict(p, [{'team':'Besiktas JK','opponent':'Example','fdr':2}])
    assert results[0]['fdr'] == 2
    assert results[0]['expected_points'] > 0

def test_missing_columns():
    with pytest.raises(ValueError):
        parse_players('name,team\nA,B\n')
