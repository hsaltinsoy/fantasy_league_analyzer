from data_sources.xgedge import parse_page

def test_player_profile_url_extracted():
    html = """<table><thead><tr><th>Player</th><th>Club</th><th>Minutes</th><th>Goals</th><th>Assists</th><th>xG</th><th>xA</th></tr></thead><tbody><tr><td><a href="/players/example">Example Player</a></td><td><a href="/super-lig/example">Example FC</a></td><td>900</td><td>3</td><td>2</td><td>3.1</td><td>1.8</td></tr></tbody></table>"""
    players, _ = parse_page(html)
    assert players[0]['profile_url'] == 'https://www.xg-edge.com/players/example'
