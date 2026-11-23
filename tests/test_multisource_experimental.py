import pytest

from analysis.multisource_experimental import evidence, rest_days_adjustment


def test_evidence_preserves_raw_values_and_provenance():
    row = evidence('football-data', 'match', 'm1', {'xg': None, 'goals': 2},
                   '2026-11-01T12:00:00Z', canonical_id='tff-12', confidence=.8)
    assert row['values'] == {'xg': None, 'goals': 2}
    assert row['provider_id'] == 'm1'
    assert row['canonical_id'] == 'tff-12'
    with pytest.raises(ValueError):
        evidence('football-data', 'match', 'm1', {}, '2026-11-01T12:00:00')


def test_rest_overlay_is_opt_in_and_rejects_future_matches():
    player = {'id': 12, 'xpts': 8.0}
    features = {'last_match_date': '2026-11-05'}
    zero = rest_days_adjustment(player, features, '2026-11-07')
    assert zero['xpts'] == 8.0
    assert zero['rest_days'] == 2
    assert rest_days_adjustment(player, features, '2026-11-07', .05)['xpts'] == 7.6
    assert player == {'id': 12, 'xpts': 8.0}
    assert rest_days_adjustment(player, {}, '2026-11-07')['rest_adjustment'] is None
    with pytest.raises(ValueError):
        rest_days_adjustment(player, features, '2026-11-04', .05)
