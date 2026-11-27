"""Official-point reconciliation and human/model selection accounting."""
from archive.analysis.phase33b_human_vs_ai import XI, BENCH, CAPTAIN, SUBSTITUTE, calculate_human, compare


def test_human_score_reconciles_with_substitution():
    actual = {i: {'points': 0} for i in XI + BENCH}
    actual[CAPTAIN]['points'] = 16
    actual[SUBSTITUTE]['points'] = 5
    actual[130]['points'] = 68
    score = calculate_human(actual)
    assert score['xi_points'] == 84
    assert score['captain_extra'] == 16
    assert score['project_scoring_total'] == 100
    assert score['conditional_substitution_total'] == 105
    assert score['unreconciled_after_murillo'] == 0


def test_comparison_separates_xi_captain_and_substitution():
    actual = {i: {'points': 0} for i in XI + BENCH}
    actual[CAPTAIN]['points'] = 16
    actual[SUBSTITUTE]['points'] = 5
    actual[130]['points'] = 68
    model = {'starting_xi': [{'id': i, 'actual_points': actual[i]['points']} for i in XI if i != 130] +
            [{'id': 999, 'actual_points': 4}], 'actual_xi_points': 16+4,
            'captain_extra_points': 3, 'actual_points': 23}
    delta = compare(actual, model)
    assert delta['xi_delta'] == 64
    assert delta['captain_delta'] == 13
    assert delta['project_scoring_gap'] == 77
    assert delta['conditional_murillo_gap'] == 82
