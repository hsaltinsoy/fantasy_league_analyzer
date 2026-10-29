from analysis.next_week_projection import project


def test_projection_matches_team_alias_and_fdr():
    players = [{'name':'A','team':'Galatasaray','minutes':720,'xg':4.0,'xa':2.0,'provider_position':'FW'}]
    fixtures = [{'team':'Galatasaray','opponent':'Fenerbahçe','venue':'home','fdr':2}]
    rows = project(players,fixtures,{'galatasaray':8})
    assert rows[0]['expected_points'] == 4.96
    assert rows[0]['expected_minutes'] == 90
    assert rows[0]['estimated_position'] == 'FWD'


def test_missing_stats_not_invented():
    rows = project([{'name':'B','team':'Galatasaray','minutes':10,'xg':None,'xa':0,'provider_position':'MF'}],
                   [{'team':'Galatasaray','opponent':'X','fdr':3}], {'galatasaray':5})
    assert rows[0]['expected_points'] is None
    assert rows[0]['projection_status'] == 'stat_missing'


def test_endpoint():
    from app import create_app
    client = create_app().test_client()
    response = client.post('/api/projections/next-week', json={'players':[], 'fixtures':[], 'team_matches':{}})
    assert response.status_code == 200
    assert response.json['projected'] == 0
