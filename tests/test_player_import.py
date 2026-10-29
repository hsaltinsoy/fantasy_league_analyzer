from data_sources.player_import import merge

def test_merge_and_missing():
    data = merge('Player,Club,Min,G,A,xG,xA\nExample,Galatasaray,800,5,2,4.5,1.2\nOther,Besiktas,300,1,0,,\n', 'name,team,price,position\nExample,Galatasaray,9.5,FWD\n')
    assert data['count'] == 2
    assert data['ready'] == 1
    assert data['players'][0]['xg'] == 4.5
    assert data['players'][1]['xg'] is None
