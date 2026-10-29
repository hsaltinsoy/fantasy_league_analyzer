from analysis.fixture_difficulty import calculate
from data_sources.football_data import parse_results, parse_fixtures


def test_form_and_fixture_rating():
    matches = parse_results('Date,HomeTeam,AwayTeam,FTHG,FTAG\n20/10/2026,A,B,2,0\n')
    fixtures = parse_fixtures('home,away,date\nA,B,2026-10-30\n')
    rows = calculate(matches, fixtures, as_of=__import__('datetime').date(2026, 10, 26))
    assert len(rows) == 2
    assert rows[0]['form']['points'] == 3
    assert rows[0]['fdr'] in range(1, 6)


def test_no_results_does_not_invent_rating():
    rows = calculate([], [{'home': 'A', 'away': 'B'}])
    assert all(r['fdr'] is None for r in rows)
