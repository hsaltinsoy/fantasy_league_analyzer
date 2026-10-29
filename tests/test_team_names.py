from data_sources.team_names import normalize_team
from data_sources.football_data import upcoming_from_results_csv
from analysis.fixture_difficulty import calculate
from datetime import date

def test_aliases():
    assert normalize_team('Beşiktaş JK') == normalize_team('Besiktas')
    assert normalize_team('Çaykur Rizespor') == normalize_team('Rizespor')
    assert normalize_team('Göztepe SK') == normalize_team('Goztepe')

def test_future_fixtures_from_single_csv():
    text = 'Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/01/2026,Besiktas,Galatasaray,1,0\n30/10/2026,Beşiktaş JK,Galatasaray,,\n31/10/2026,Goztepe,Rizespor,,\n20/11/2026,Fenerbahce,Trabzonspor,,\n'
    fixtures = upcoming_from_results_csv(text, date(2026, 10, 26))
    assert len(fixtures) == 2
    assert fixtures[0]['date'] == '2026-10-30'

def test_names_join_across_files():
    matches = [{'date':'2026-10-01','home':'Besiktas','away':'Galatasaray','home_goals':2,'away_goals':1}]
    fixtures = [{'date':'2026-10-30','home':'Beşiktaş JK','away':'Galatasaray'}]
    rows = calculate(matches, fixtures, as_of=date(2026,10,26))
    assert all(row['fdr'] is not None for row in rows)
