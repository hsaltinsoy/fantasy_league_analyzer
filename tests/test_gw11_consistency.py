from analysis.lineup_snapshot import fingerprint
from analysis.predict_next_week import annotate_player_changes


def test_input_fingerprint_normalizes_equivalent_zero_weights():
    args = (11, [{'id': 1}], {'1': [{'gameweekOrder': 10, 'points': 4}]},
            {'matches': [{'id': 12}]}, 'short_form_3w', 'balanced')
    assert fingerprint(*args, 0) == fingerprint(*args, 0.0)
    assert fingerprint(*args, 0) != fingerprint(*args, .05)


def test_display_delta_uses_final_returned_xpts_and_handles_missing():
    players = [{'baseline_xpts': 4.665, 'xpts': 4.675},
               {'baseline_xpts': 0, 'xpts': 1},
               {'baseline_xpts': None, 'xpts': 1},
               {'baseline_xpts': 1, 'xpts': None}]
    annotate_player_changes(players)
    assert players[0]['absolute_delta'] == players[0]['xpts'] - players[0]['baseline_xpts']
    assert players[0]['percentage_delta'] == 100 * (4.675 - 4.665) / 4.665
    assert players[1]['percentage_delta'] is None
    assert players[2]['absolute_delta'] is None
    assert players[3]['percentage_delta'] is None
