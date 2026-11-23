from analysis.verified_fixtures_v36 import make_optimizer


def test_captain_risk_discount_is_separate_from_fantasy_multiplier():
    player = {'id': 12, 'xpts': 9.266}
    rows = [{'gameweekOrder': week, 'points': points, 'minutesPlayed': 90}
            for week, points in enumerate((0, 20, 0, 20, 0), 1)]
    captured = []

    def capture(pool):
        captured.extend(pool)
        return {}

    make_optimizer([({'id': 12}, rows)], 11, .2, 0,
                   optimizer_func=capture)([player])
    assert captured[0]['captain_bonus_xpts'] < 9.266
    assert captured[0]['xpts'] == 9.266
    assert round(65.52 + captured[0]['xpts'], 3) == 74.786
