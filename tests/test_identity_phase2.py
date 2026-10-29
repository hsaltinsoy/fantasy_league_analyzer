from data_sources.identity import normalize, resolve_players, add_verified_identity, load_crosswalk
from data_sources.fixture_validation import validate_week


def test_turkish_name_and_duplicate_disambiguation():
    players=[{'id':1,'name':'Çağrı Işık','club_name':'Beşiktaş','position':'MID'}]
    external=[{'name':'Cagri Isik','team':'Beşiktaş','xg':1,'xa':0.5},
              {'name':'Cagri Isik','team':'Galatasaray','xg':2,'xa':1}]
    resolved,report=resolve_players(players,external)
    assert normalize('Çağrı Işık')==normalize('Cagri Isik')
    assert resolved[0]['external_statistics']['xg']==1
    assert report['matched_players']==1
    assert resolved[0]['position']=='MID'


def test_duplicate_names_without_club_are_ambiguous():
    player={'id':1,'name':'Ali Demir','position':'DEF'}
    external=[{'name':'Ali Demir','team':'A'}, {'name':'Ali Demir','team':'B'}]
    rows,report=resolve_players([player],external)
    assert rows[0]['external_statistics'] is None
    assert report['ambiguous_matches']==1


def test_verified_stable_profile_survives_transfer(tmp_path):
    path=tmp_path/'crosswalk.json'
    url='https://www.xg-edge.com/players/ali-demir'
    version=add_verified_identity(7,url,'reviewed official player page',path=path)
    player={'id':7,'name':'Ali Demir','club_name':'New Club','position':'FWD'}
    external=[{'name':'Ali Demir','team':'Old Club','profile_url':url,'xg':None,'xa':1}]
    rows,report=resolve_players([player],external,load_crosswalk(path))
    assert rows[0]['identity_confidence']=='verified'
    assert rows[0]['missing_external_statistics']
    assert report['crosswalk_version']==version


def test_incorrect_club_association_is_not_merged():
    rows,report=resolve_players([{'id':1,'name':'Ali Demir','club_name':'Beşiktaş'}],
                                [{'name':'Ali Demir','team':'Galatasaray','xg':2,'xa':1}])
    assert rows[0]['external_statistics'] is None
    assert report['ambiguous_matches']==1


def test_fixture_gaps_postponement_and_double_round():
    matches=[{'id':1,'homeClubId':1,'awayClubId':2,'kickoffAt':'2026-10-30T10:00:00Z','status':'POSTPONED'},
             {'id':2,'homeClubId':1,'awayClubId':3,'kickoffAt':'2026-10-31T10:00:00Z','status':'NS'}]
    report=validate_week({'matches':matches},[{'club_id':1},{'club_id':4}])
    assert report['fixture_coverage']['double_fixture_teams']==['1']
    assert report['fixture_coverage']['missing_teams']==['4']
    assert any('postponed' in x for x in report['warnings'])
