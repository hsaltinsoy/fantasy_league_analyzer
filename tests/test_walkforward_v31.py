import json
import pytest
from analysis.walkforward_v31 import audit_fixture_snapshot, walk_forward


def test_missing_snapshot():
    assert audit_fixture_snapshot(None, [5])['usable_for_prediction'] is False


def test_snapshot_audit(tmp_path):
    p = tmp_path/'fixtures.json'
    p.write_text(json.dumps({'weeks':{'5':{'captured_utc':'2026-08-01T10:00:00Z','deadline_utc':'2026-08-02T10:00:00Z','source':'official','matches':[{'home_club_id':1,'away_club_id':2}]}}}))
    result = audit_fixture_snapshot(p, [5,6])
    assert result['weeks']['5']['status'] == 'timestamp_before_deadline'
    assert result['weeks']['6']['status'] == 'missing'
    assert result['usable_for_prediction'] is False


def test_bad_thresholds():
    with pytest.raises(ValueError):
        walk_forward([], thresholds=[1.2])
    with pytest.raises(ValueError):
        walk_forward([], thresholds=[.25,.25])


def test_bad_weeks():
    with pytest.raises(ValueError):
        walk_forward([], weeks=[6,5])
