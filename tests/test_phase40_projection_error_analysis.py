from analysis.phase40_projection_error_analysis import feasible_replacement, run, summary


def test_summary_preserves_prediction_error_definition():
    rows = [{'predicted': 4, 'actual': 0}, {'predicted': 2, 'actual': 4}]
    result = summary(rows)
    assert result['mae'] == 3
    assert result['rmse'] == 3.162


def test_direct_replacement_respects_position_budget_and_club():
    squad = [
        {'id': 1, 'position': 'DEF', 'price': 50, 'team': 1},
        {'id': 2, 'position': 'FWD', 'price': 40, 'team': 2},
    ]
    assert feasible_replacement({'id': 3, 'position': 'DEF', 'price': 55, 'team': 3}, squad)
    assert not feasible_replacement({'id': 3, 'position': 'MID', 'price': 1, 'team': 3}, squad)
    assert not feasible_replacement({'id': 3, 'position': 'DEF', 'price': 70, 'team': 3}, squad)


def test_phase36_gw11_reconciliation_is_outcome_only():
    result = run()
    week = result['weeks']['11']
    h = week['human_vs_model']
    assert len(week['xi_ids']) == 11
    assert len(week['bench_ids']) == 4
    assert h['model_project_scoring_actual'] == 70
    assert h['human_project_scoring_actual'] == 100
    assert h['human_reported_auto_sub_points'] == 5
    assert h['actual_selection_component'] + h['actual_captain_component'] == -30
    assert abs(h['selection_component'] + h['captain_component'] + h['bench_component'] - h['objective_gap']) < .0002
