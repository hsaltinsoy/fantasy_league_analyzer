from datetime import datetime, timezone, timedelta
import pytest

from data_sources.provider_evidence import (EntityMatch, EvidenceBatch, EvidenceRecord,
    EvidenceValue, MissingReason, require_complete)
from data_sources.official_history_quality import audit_expected_metrics, expected_metric

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def record(**changes):
    values = dict(kind='player_stat', provider_entity_id='123', match=None,
        event_at=NOW-timedelta(days=1), published_at=NOW-timedelta(hours=1),
        fields=(EvidenceValue('minutes', 90, 'minutesPlayed'),))
    values.update(changes)
    return EvidenceRecord(**values)


def batch(**changes):
    values = dict(provider='example', endpoint='https://example.invalid/stats',
        retrieved_at=NOW, source_sha256='a'*64, competition_id='TR1',
        season='2026-27', records=(record(),), complete=True)
    values.update(changes)
    return EvidenceBatch(**values)


def test_evidence_requires_provenance_and_explicit_missing():
    with pytest.raises(ValueError):
        EvidenceValue('xG', None, 'xG')
    with pytest.raises(ValueError):
        EvidenceValue('xG', 0, 'xG', MissingReason.NOT_REPORTED)
    with pytest.raises(ValueError):
        batch(complete=False)
    with pytest.raises(ValueError):
        EntityMatch('12', '507', .99, 'name_only')


def test_provider_failure_and_leakage_fail_closed():
    assert require_complete(batch(), kind='player_stat', cutoff=NOW)
    with pytest.raises(ValueError):
        require_complete(batch(complete=False, missing_reason=MissingReason.NOT_COVERED),
                         kind='player_stat', cutoff=NOW)
    with pytest.raises(ValueError):
        batch(retrieved_at=NOW+timedelta(seconds=1)).before(NOW)
    with pytest.raises(ValueError):
        batch(records=(record(published_at=NOW+timedelta(seconds=1)),)).before(NOW)
    with pytest.raises(ValueError):
        batch(records=(record(event_at=NOW),)).before(NOW)


def test_future_fixture_is_allowed_when_its_schedule_was_observed_before_cutoff():
    fixture = record(kind='fixture', event_at=NOW+timedelta(days=1),
                     published_at=NOW-timedelta(hours=1))
    assert require_complete(batch(records=(fixture,)), kind='fixture', cutoff=NOW)


def test_all_zero_official_expected_fields_are_unavailable_not_zero():
    rows = {'507': [{'gameweekOrder': 11, 'minutesPlayed': 90, 'goals': 1,
                     'assists': 0, 'xG': 0, 'xA': 0}]}
    quality = audit_expected_metrics(rows, retrieved_at=NOW.isoformat(), source_url='official')
    assert quality['fields']['xG']['quality'] == 'suspected_unpopulated'
    assert expected_metric(rows['507'][0], 'xG', quality).value is None
    assert expected_metric(rows['507'][0], 'xA', quality).missing_reason == MissingReason.UNPOPULATED_FIELD
    assert rows['507'][0]['xG'] == 0


def test_measured_zero_remains_zero_when_distribution_is_populated():
    rows = {'1': [{'minutesPlayed': 90, 'goals': 1, 'assists': 0, 'xG': 0.6, 'xA': 0.0}],
            '2': [{'minutesPlayed': 90, 'goals': 0, 'assists': 1, 'xG': 0.0, 'xA': 0.3}]}
    quality = audit_expected_metrics(rows, retrieved_at=NOW.isoformat(), source_url='official')
    assert expected_metric(rows['2'][0], 'xG', quality).value == 0.0
    assert expected_metric(rows['1'][0], 'xA', quality).value == 0.0
