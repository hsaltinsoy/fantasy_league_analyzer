from data_sources.fixture_supplement import supplement
from data_sources.team_names import normalize_team

class Response:
    content = b'Date,HomeTeam,AwayTeam\n31/10/2026,Erzurumspor FK,Corum FK\n31/10/2026,Galatasaray,Other\n'
    def raise_for_status(self): pass

def test_supplement_missing_fixture():
    fixtures = [{'date':'2026-10-30','home':'Galatasaray','away':'Konyaspor'}]
    merged, notes = supplement(fixtures, '2627', lambda *args, **kwargs: Response())
    assert len(merged) == 2
    assert normalize_team(merged[1]['away']) == 'corum'
    assert '1 fixtures' in notes[0]

def test_aliases():
    assert normalize_team('Arca Çorum FK') == normalize_team('Çorum FK')
    assert normalize_team('Erzurumspor FK') == normalize_team('Erzurumspor')
