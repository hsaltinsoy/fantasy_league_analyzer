from data_sources.sportscore_players import fetch_players

class Response:
    def __init__(self, data): self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data

def test_merge_goals_assists_and_missing_values():
    def fake_get(url, params, **kwargs):
        if params['stat'] == 'goals':
            return Response({'players':[{'player':{'id':10,'name':'Sample A'},'team':{'name':'Galatasaray'},'goals':4}]})
        return Response({'players':[{'player':{'id':10,'name':'Sample A'},'team':{'name':'Galatasaray'},'assists':2},
                                    {'player':{'id':11,'name':'Sample B'},'team':{'name':'Besiktas'},'assists':1}]})
    result=fetch_players(get=fake_get)
    assert result['count']==2
    assert result['players'][0]['goals']==4
    assert result['players'][0]['assists']==2
    assert result['players'][1]['goals'] is None
    assert 'fantasy_price' in result['missing']

def test_unsupported_league_returns_no_invented_players():
    result=fetch_players(get=lambda *a, **k: Response({'players':[]}))
    assert result['players']==[]
