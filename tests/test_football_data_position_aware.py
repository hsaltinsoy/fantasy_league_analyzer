from analysis.football_data_position_aware import clamp, relative, signal


def test_bounds_and_missing_features():
    assert clamp(100) == 1
    assert clamp(-100) == -1
    assert relative(None, 1.5) == 0
    assert signal({'position': 'GK', 'football_data': None}, {'xg': 1.5, 'sot': 4})[0] == 0


def test_goalkeeper_shots_do_not_override_high_opponent_xg():
    evidence = {'team': {'xg_against': 1.5}, 'opponent_attacking_strength': 2.5,
                'opponent_shots_on_target': 12, 'expected_clean_sheet_indicator': .08}
    raw, drivers = signal({'position': 'GK', 'football_data': evidence}, {'xg': 1.5, 'sot': 4})
    assert drivers['gated_save_volume'] == 0
    assert raw < 0


def test_positions_use_distinct_signals():
    evidence = {'team': {'xg_for': 2, 'xg_against': 1, 'last3_xg_for': 2.2,
                'last5_xg_for': 1.8, 'home_xg_for': 2.4, 'home_xg_against': .8,
                'last3_shots_on_target': 6, 'last5_shots_on_target': 5},
                'opponent_defensive_xg_conceded': 2,
                'opponent_attacking_strength': 1,
                'expected_clean_sheet_indicator': .37,
                'opponent_shots_on_target': 4}
    reference = {'xg': 1.5, 'sot': 4}
    values = [signal({'position': pos, 'home': True, 'football_data': evidence}, reference)[0]
              for pos in ('FWD', 'MID', 'DEF', 'GK')]
    assert len(set(values)) == 4
    assert all(-1 <= value <= 1 for value in values)
