import pytest

from analysis.capture_integrity import classify, digest, validate_inputs


def test_deterministic_input_digest_and_complete_pool():
    players = [{'id': 1, 'name': 'A', 'club_id': 2, 'position': 'MID', 'price': 5}]
    histories = [{'player_id': 1, 'rows': [{'gameweekOrder': 9, 'points': 2}]}]
    value = validate_inputs(10, players, [{'id': 3}], histories)
    assert value == validate_inputs(10, players, [{'id': 3}], histories)
    assert value != digest({'week': 10})
    with pytest.raises(ValueError, match='Future'):
        validate_inputs(10, players, [{'id': 3}], [{'player_id': 1,
                        'rows': [{'gameweekOrder': 10, 'points': 99}]}])
    with pytest.raises(ValueError, match='Complete'):
        validate_inputs(10, players, [], histories)


def test_deadline_classification_and_observation_times():
    capture = '2026-11-01T10:00:00Z'
    deadline = '2026-11-01T12:00:00Z'
    assert classify(capture, deadline, 'official', {'players': capture}) == 'local_pre_deadline_unverified'
    assert classify(capture, None, None) == 'unknown_deadline'
    assert classify('2026-11-01T13:00:00Z', deadline, 'official') == 'post_deadline'
    with pytest.raises(ValueError, match='observation'):
        classify(capture, deadline, 'official', {'players': '2026-11-01T11:00:00Z'})
