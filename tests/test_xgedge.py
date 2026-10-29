from data_sources.xgedge import parse_page, fetch_players, PlayerFeedError
import pytest
HTML='''<table><thead><tr><th>#</th><th>Player</th><th>Club</th><th>Pos</th><th>Min</th><th>G</th><th>A</th><th>xG</th><th>xA</th><th>xGI</th></tr></thead><tbody><tr><td>1</td><td>Test Player</td><td>Galatasaray</td><td>F</td><td>650</td><td>4</td><td>2</td><td>5.2</td><td>1.4</td><td>6.6</td></tr></tbody></table>'''
def test_parse():
    players,_=parse_page(HTML)
    assert players[0]['xg']==5.2
    assert players[0]['price'] is None
    assert players[0]['name']=='Test Player'
def test_no_table():
    with pytest.raises(PlayerFeedError):parse_page('<html></html>')


def test_empty_player_table_is_not_accepted_as_complete_feed():
    from unittest.mock import Mock
    session = Mock()
    session.get.side_effect = [Mock(status_code=200, text='User-agent: *\nAllow: /'),
                               Mock(status_code=200, text=HTML.split('<tbody>')[0] + '<tbody></tbody></table>', raise_for_status=Mock())]
    with pytest.raises(PlayerFeedError, match='boş'):
        fetch_players(session=session)
def test_invalid_pages():
    with pytest.raises(ValueError):fetch_players(max_pages=99)

def test_semantic_player_and_team_links():
    html = '''<table><thead><tr><th>#</th><th>Player</th><th>Club</th><th>Pos</th><th>Min</th><th>G</th><th>A</th><th>xG</th><th>xA</th></tr></thead><tbody><tr><td>1</td><td><a href="/players/mason-greenwood">Mason Greenwood</a></td><td><a href="/super-lig/fenerbahce">Fenerbahçe</a></td><td>F</td><td>597</td><td>4</td><td>2</td><td>5.66</td><td>1.69</td></tr></tbody></table>'''
    players, _ = parse_page(html)
    assert players[0]['name'] == 'Mason Greenwood'
    assert players[0]['team'] == 'Fenerbahçe'
    assert players[0]['minutes'] == 597

def test_reject_team_as_player():
    html = HTML.replace('Test Player', 'Galatasaray')
    with pytest.raises(PlayerFeedError, match='takım adıyla aynı'):
        parse_page(html)

def test_reject_shifted_numeric_columns():
    html = HTML.replace('<td>650</td><td>4</td><td>2</td><td>5.2</td><td>1.4</td>', '<td>8</td><td>3</td><td>6.67</td><td>0.93</td><td>7.6</td>')
    with pytest.raises(PlayerFeedError, match='tam sayı'):
        parse_page(html)

def test_reject_extra_cell_even_if_links_correct():
    html = HTML.replace('<td>1</td>', '<td>1</td><td>extra</td>')
    with pytest.raises(PlayerFeedError, match='hücre'):
        parse_page(html)

def test_reject_ambiguous_per90_header():
    html = HTML.replace('<th>Min</th>', '<th>Min/90</th>')
    with pytest.raises(PlayerFeedError, match='sütunları eksik'):
        parse_page(html)


def test_missing_xg_does_not_abort_other_players():
    html = HTML.replace('<td>5.2</td>', '<td>—</td>')
    players, _ = parse_page(html)
    assert players[0]['xg'] is None
    assert players[0]['xa'] == 1.4
    assert players[0]['missing_stats'] == ['xg']


def test_missing_xa_column_is_optional():
    html = HTML.replace('<th>xA</th>', '').replace('<td>1.4</td>', '')
    players, _ = parse_page(html)
    assert players[0]['xa'] is None
    assert players[0]['xg'] == 5.2
