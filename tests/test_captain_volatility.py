from analysis.verified_fixtures_v36 import make_optimizer


def test_captain_risk_uses_weekly_points_instead_of_cumulative_total():
    player = {'id': 1, 'xpts': 10.0}
    rows = [{'gameweekOrder': week, 'points': 3, 'totalPoints': 3 * week,
             'minutesPlayed': 90} for week in range(1, 6)]
    captured = []

    def capture(pool):
        captured.extend(pool)
        return {}

    make_optimizer([({'id': 1}, rows)], 6, captain_risk=.2, minutes_risk=0,
                   optimizer_func=capture)([player])
    assert captured[0]['captain_bonus_xpts'] == 10.0
