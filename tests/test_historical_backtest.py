import json
from analysis import historical_backtest as hb


def test_pool_uses_only_prior_rounds(tmp_path, monkeypatch):
    monkeypatch.setattr(hb, 'STORE', tmp_path)
    (tmp_path / 'players.json').write_text(json.dumps([{'id': 1, 'name': 'A', 'team': '1', 'position': 'MID'}]))
    (tmp_path / 'player_1.json').write_text(json.dumps([
        {'gameweekOrder': 8, 'points': 2, 'minutesPlayed': 90, 'cost': 5},
        {'gameweekOrder': 9, 'points': 30, 'minutesPlayed': 90, 'cost': 20},
    ]))
    pool, actual, coverage = hb.build_pool(9)
    assert pool[0]['price'] == 5
    assert pool[0]['xpts'] < 10
    assert actual['1'] == 30
