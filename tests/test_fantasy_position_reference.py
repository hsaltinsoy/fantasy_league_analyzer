from data_sources.fantasy_position_reference import verified_position
from analysis.next_week_projection import project

def test_known_forward_positions():
    assert verified_position('Eldor Shomurodov', 'Başakşehir FK') == 'FWD'
    assert verified_position('Gift Orban', 'Amed Sportif Faaliyetler') == 'FWD'
    assert verified_position('Adrian Benedyczak', 'Kasımpaşa') == 'FWD'
    assert verified_position('Gift Orban', 'Galatasaray') is None

def test_verified_position_overrides_provider_and_reports_conflict():
    result = project([{'name':'Gift Orban','team':'Amed Sportif Faaliyetler','provider_position':'M','minutes':500,'xg':3,'xa':1}],
                     [{'team':'Amed Sportif Faaliyetler','opponent':'Eyüpspor','venue':'home','fdr':2}],
                     {'amedspor':7})[0]
    assert result['estimated_position'] == 'FWD'
    assert result['position_conflict'] is True
    assert result['position_source'] == 'public_fantasy_reference_2026_10_27'
    assert result['expected_points'] is not None
