from analysis.capture_integrity import validate_inputs
from analysis.six_model_batch import NAMES, replay


def bundle():
    players = [{'id': i, 'name': f'P{i}', 'team': str(i % 2 + 1),
                'position': ('GK' if i < 3 else 'DEF' if i < 8 else
                             'MID' if i < 13 else 'FWD'), 'price': 5}
               for i in range(1, 16)]
    fixtures = [{'id': 1, 'homeClubId': 1, 'awayClubId': 2}]
    histories = [{'player_id': i, 'rows': [{'gameweekOrder': 9, 'points': 2}]}
                 for i in range(1, 16)]
    return {'gameweek': 10, 'players': players, 'fixtures': fixtures,
            'histories': histories, 'input_hash': validate_inputs(10, players, fixtures, histories),
            'cutoff_utc': '2026-11-01T10:00:00Z',
            'deadline_at': '2026-11-01T12:00:00Z',
            'external_matches': [{'id': 1}], 'team_features': {}, 'fixture_date': None}


def test_six_variants_share_frozen_inputs_and_are_offline(monkeypatch):
    seen = []
    monkeypatch.setattr('analysis.six_model_batch.make_adjuster_from_matches',
                        lambda *args: (lambda pool: pool, {}))
    def predictor(week, players, records, fixtures, tow, **kwargs):
        seen.append(([p['id'] for p in players], [r[1][0]['points'] for r in records]))
        return {'week': week, 'starting_xi': players[:11], 'bench': players[11:],
                'expected_points': 22, 'risk_adjusted_objective': 22}
    result = replay(bundle(), predictor=predictor)
    assert result['status'] == 'complete'
    assert set(result['predictions']) == set(NAMES)
    assert len(set(map(str, seen))) == 1
    assert result['predictions']['rest_days_control']['benchmark']['rest_weight'] == 0


def test_partial_variant_failure_never_returns_valid_batch(monkeypatch):
    monkeypatch.setattr('analysis.six_model_batch.make_adjuster_from_matches',
                        lambda *args: (lambda pool: pool, {}))
    def predictor(week, players, records, fixtures, tow, **kwargs):
        if kwargs['model'] == 'stable_8w':
            raise ValueError('insufficient history')
        return {'week': week}
    result = replay(bundle(), predictor=predictor)
    assert result['status'] == 'incomplete'
    assert result['predictions'] == {}
    assert 'failed' in result['statuses']['stable_8w']
