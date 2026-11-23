import pytest

from analysis.optimizer import _optimize_formation


def test_forced_player_must_exist_in_eligible_pool():
    players = [{'id': i, 'position': ('GK' if i < 3 else 'DEF' if i < 8
                else 'MID' if i < 13 else 'FWD'), 'team': str(i),
                'price': 4, 'xpts': 1, 'name': str(i)} for i in range(1, 16)]
    with pytest.raises(ValueError, match='not in the eligible pool'):
        _optimize_formation(players, (3, 4, 3), force_start_ids=(999,))
