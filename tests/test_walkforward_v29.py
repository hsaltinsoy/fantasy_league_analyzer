from analysis.walkforward_v29 import player_adjustment, captain_risk, walk_forward


def rows(points):
    return [{'gameweekOrder': i + 1, 'points': p} for i, p in enumerate(points)]


def test_adjustment_uses_prior_only():
    history = rows([2, 2, 2, 9, 9, 100])
    assert player_adjustment(history, 6) == player_adjustment(history[:-1], 6)
    assert player_adjustment(history, 6) > 0
    assert player_adjustment(history, 7) != player_adjustment(history, 6)


def test_captain_risk():
    assert captain_risk(rows([3, 3, 3, 100]), 4) == 0
    assert captain_risk(rows([1, 10, 1, 100]), 4) > 0


def test_walkforward_only_prior_outcomes():
    def evaluator(records, week, config, weight, threshold, cal, cap, optimizer):
        actual = 20 + (week - 5) * 3 + cal * 2 - cap * 5
        return {'predicted': 30, 'actual': actual, 'absolute_error': abs(30 - actual)}
    report = walk_forward([], [5, 6], evaluator=evaluator)
    assert report['weeks'][0]['selected_model'] is None
    assert report['weeks'][1]['training_weeks'] == [5]
    assert report['summary']['scored_weeks'] == 1
