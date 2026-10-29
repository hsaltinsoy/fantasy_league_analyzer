from analysis.chips import scenarios, last_round_players

def test_scenarios():
    players=[{'id':i,'xpts':float(i)} for i in range(1,16)]
    sol={'starting_xi':players[:11],'squad':players,'captain':players[10]}
    rows=scenarios(sol)
    assert rows[0]['projected_total']==77.0
    assert rows[1]['projected_total']==88.0
    assert rows[2]['projected_total']==99.0
    assert rows[3]['projected_total']==131.0
    assert rows[4]['projected_total'] is None

def test_last_round():
    result=last_round_players([{'id':1,'round_points':2,'name':'A'},{'id':2,'round_points':9,'name':'B'},{'id':3,'round_points':None}])
    assert result['players'][0]['name']=='B'
    assert result['count']==2
