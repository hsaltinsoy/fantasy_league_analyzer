from analysis.walkforward_v28 import calibrate, candidate_rank, walk_forward


def test_shrunk_and_capped_calibration():
    assert calibrate(80, [{'actual': 0, 'predicted': 100}]*10) == (68.0, -12.0)
    assert calibrate(80, []) == (80, 0.0)
    assert calibrate(80, [{'actual': 60, 'predicted': 80}]) == (76.0, -4.0)


def test_risk_penalizes_variance():
    stable = [{'actual': 50}]*3
    volatile = [{'actual': 20}, {'actual': 50}, {'actual': 80}]
    assert candidate_rank(stable) > candidate_rank(volatile)


def test_current_week_actual_does_not_change_selection_or_forecast():
    def run(target):
        def evaluator(records, week, config, fixture_weight, min_participation, optimizer):
            # v2.8 runs all 8 candidates; mock their outcomes consistently
            points = 40 if week == 5 else target
            return {'predicted': 60.0, 'actual': points,
                    'absolute_error': abs(60-points), 'formation': '4-4-2',
                    'captain': 'Example'}
        return walk_forward([], (5, 6), evaluator=evaluator)
    a, b = run(20), run(100)
    assert a['weeks'][1]['selected_model'] == b['weeks'][1]['selected_model']
    assert a['weeks'][1]['result']['calibrated_predicted'] == b['weeks'][1]['result']['calibrated_predicted']
    assert a['weeks'][1]['result']['raw_predicted'] == b['weeks'][1]['result']['raw_predicted']


def test_no_target_week_calibration():
    rows = [{'predicted': 80, 'actual': 50}]
    assert calibrate(70, rows)[0] == 64.0
    assert calibrate(70, rows)[0] == 64.0
