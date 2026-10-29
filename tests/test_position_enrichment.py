from data_sources.position_enrichment import classify, parse_profile_position, enrich
from data_sources.team_names import normalize_team
from analysis.next_week_projection import project

def test_position_parsing():
    assert classify('Centre-Back') == 'DEF'
    assert classify('Midfielder') == 'MID'
    assert parse_profile_position('<dl><dt>Position</dt><dd>Striker</dd></dl>') == 'FWD'
    assert parse_profile_position('<div>Position: Unknown</div>') is None

def test_team_aliases():
    assert normalize_team('Başakşehir FK') == normalize_team('İstanbul Başakşehir')
    assert normalize_team('Amed Sportif Faaliyetler') == 'amedspor'

def test_fixture_diagnostic():
    rows=project([{'name':'X','team':'Amed Sportif Faaliyetler'}], [], {})
    assert rows[0]['projection_status']=='fixture_missing'
    assert rows[0]['fixture_note']


def test_xgedge_single_letter_positions():
    from data_sources.position_enrichment import classify
    from analysis.next_week_projection import POSITION_MAP
    for raw, expected in [('G','GK'),('D','DEF'),('M','MID'),('F','FWD')]:
        assert classify(raw) == expected
        assert POSITION_MAP[raw.lower()] == expected

def test_projection_accepts_provider_letter_position():
    rows = project(
        [{'name':'Test', 'team':'Galatasaray', 'provider_position':'F', 'minutes':450,'xg':3.0,'xa':1.0}],
        [{'team':'Galatasaray','opponent':'Konyaspor','venue':'away','fdr':3}],
        {'galatasaray':6}
    )
    assert rows[0]['estimated_position'] == 'FWD'
    assert rows[0]['projection_status'] == 'estimated_partial'
    assert rows[0]['expected_points'] is not None
