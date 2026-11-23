from analysis.phase23b_audit import build


def test_missing_prededline_snapshots_are_blocked(tmp_path):
    result = build(tmp_path)
    assert result['eligible_full_squad_evaluation_weeks'] == []
    assert result['requested_ablations']['rest_days']['status'] == 'blocked'
    assert result['existing_form_component_report']['sha256'] is None
