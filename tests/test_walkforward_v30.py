from analysis.walkforward_v30 import walk_forward, minutes_audit


def test_reject_unsorted_weeks():
    try:
        walk_forward([], (7, 6))
        assert False
    except ValueError:
        pass


def test_reject_invalid_threshold():
    try:
        walk_forward([], (5, 6), min_participation=1.5)
        assert False
    except ValueError:
        pass


def test_minutes_audit_does_not_change_team():
    records = [({'id': 1}, [{'gameweekOrder': 5, 'minutesPlayed': 90},
                             {'gameweekOrder': 6, 'minutesPlayed': 0}])]
    result = {'starting_xi': [{'id': 1, 'name': 'Test'}]}
    audit = minutes_audit(records, 6, result)
    assert audit['xi_did_not_play'] == 1
    assert audit['xi_under_60_minutes'] == 1
    assert audit['players'][0]['previous_four_avg_minutes'] == 90
