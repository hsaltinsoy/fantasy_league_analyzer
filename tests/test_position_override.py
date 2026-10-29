from analysis.next_week_projection import project

def test_shomurodov_is_forward_even_when_provider_says_mid():
    players = [{'name':'Eldor Shomurodov','team':'Başakşehir FK','provider_position':'M','minutes':900,'xg':4.0,'xa':1.0}]
    fixtures = [{'team':'Başakşehir FK','opponent':'Samsunspor','venue':'home','fdr':1}]
    rows = project(players,fixtures,{'basaksehir':10})
    assert rows[0]['estimated_position'] == 'FWD'
    assert rows[0]['expected_points'] is not None

def test_other_midfielder_not_overridden():
    players = [{'name':'Another Player','team':'Başakşehir FK','provider_position':'M','minutes':900,'xg':4.0,'xa':1.0}]
    fixtures = [{'team':'Başakşehir FK','opponent':'Samsunspor','venue':'home','fdr':1}]
    assert project(players,fixtures,{'basaksehir':10})[0]['estimated_position'] == 'MID'
