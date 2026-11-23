import pytest

from analysis.history_freshness import audit, require_capture_ready


def evidence(*, partial=False):
    players = [{'id': 1}, {'id': 2}]
    history = {'1': [{'gameweekOrder': 9, 'points': 3},
                     {'gameweekOrder': 10, 'points': 2}],
               '2': [{'gameweekOrder': 9, 'points': 1},
                     {'gameweekOrder': 10, 'points': 0}]}
    complete = {'status': 'FT', 'homeScore': 1, 'awayScore': 0}
    pending = {'status': 'SCHEDULED', 'homeScore': None, 'awayScore': None}
    fixtures = {'captured_utc': '2026-11-07T12:00:00Z',
                'weeks': {'10': {'matches': [complete]},
                          '11': {'matches': [complete, pending] if partial else []}}}
    return players, history, fixtures


def test_fresh_and_individual_missing_history():
    players, histories, fixtures = evidence()
    report = audit(12, players, histories, fixtures)
    assert report['status'] == 'fresh'
    assert report['latest_completed_gameweek'] == 10
    assert report['up_to_date_percentage'] == 100
    require_capture_ready(report)
    histories['2'] = []
    report = audit(12, players, histories, fixtures)
    assert report['status'] == 'partial_player_coverage'
    assert report['players_with_up_to_date_history'] == 1


def test_confirmed_ingestion_failure_and_unknown_source():
    players, histories, fixtures = evidence(partial=True)
    histories = {pid: rows[:1] for pid, rows in histories.items()}
    unknown = audit(12, players, histories, fixtures)
    assert unknown['status'] == 'source_availability_unknown'
    assert unknown['partial_gameweeks'] == [11]
    with pytest.raises(ValueError, match='source_availability_unknown'):
        require_capture_ready(unknown)
    probe = {'source':'official_tff_history_api', 'retrieved_at':'2026-11-07T12:10:00Z',
             'gameweek':10, 'available_player_ids':['1']}
    confirmed = audit(12, players, histories, fixtures, source_probe=probe)
    assert confirmed['status'] == 'confirmed_ingestion_failure'
    with pytest.raises(ValueError, match='confirmed_ingestion_failure'):
        require_capture_ready(confirmed)


def test_source_unavailable_requires_explicit_documented_override():
    players, histories, fixtures = evidence()
    histories = {pid: rows[:1] for pid, rows in histories.items()}
    probe = {'source':'official_tff_history_api', 'retrieved_at':'2026-11-07T12:10:00Z',
             'gameweek':10, 'available_player_ids':[], 'sampled_player_count':2,
             'status':'unavailable'}
    blocked = audit(12, players, histories, fixtures, source_probe=probe)
    assert blocked['status'] == 'source_unavailable_requires_override'
    with pytest.raises(ValueError):
        require_capture_ready(blocked)
    allowed = audit(12, players, histories, fixtures, source_probe=probe,
                    allow_source_unavailable=True)
    assert allowed['status'] == 'source_unavailable'
    require_capture_ready(allowed)


def test_target_leakage_and_partial_week_history_rejected():
    players, histories, fixtures = evidence(partial=True)
    histories['1'].append({'gameweekOrder': 12, 'points': 1})
    with pytest.raises(ValueError, match='Target-week'):
        audit(12, players, histories, fixtures)
    histories['1'].pop()
    histories['1'].append({'gameweekOrder': 11, 'points': 1})
    report = audit(12, players, histories, fixtures)
    assert report['status'] == 'unfinalized_history_present'
    with pytest.raises(ValueError):
        require_capture_ready(report)


def test_capture_rejects_incomplete_refresh_before_prediction(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from analysis.prospective_monitor import capture
    from analysis.live_benchmark import FIXTURE_ENDPOINT
    from data_sources.tff_official import BASE

    now = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    players = [{'id': 1, 'name': 'P1', 'club_id': 1, 'position': 'MID',
                'price': 5, 'availability': 'AVAILABLE'}]
    records = [(players[0], [{'gameweekOrder': 9, 'points': 2}])]
    archive = {'source_endpoint': FIXTURE_ENDPOINT,
               'source_url': BASE + FIXTURE_ENDPOINT,
               'captured_utc': now.isoformat(),
               'weeks': {'10': {'gameweek_id': 10, 'matches': [
                            {'status': 'FT', 'homeScore': 1, 'awayScore': 0}]},
                         '12': {'gameweek_id': 12, 'deadline':
                                '2026-11-21T09:30:00Z', 'matches': [
                                {'id': 12, 'homeClubId': 1, 'awayClubId': 2,
                                 'kickoffAt': '2026-11-22T12:00:00Z',
                                 'status': 'SCHEDULED'}]}}}
    monkeypatch.setattr('analysis.live_benchmark.generate',
                        lambda **kwargs: pytest.fail('prediction ran after stale history'))
    with pytest.raises(ValueError, match='source_unavailable_requires_override'):
        capture(path=tmp_path/'tracking.sqlite3', fixture_archive=archive,
                players_provider=lambda: {'players': players},
                records_provider=lambda: records, now=now,
                history_probe_provider=lambda *args: {'source':'official_tff_history_api',
                    'retrieved_at': now.isoformat(), 'gameweek': 10,
                    'available_player_ids':['1'], 'status':'available'},
                history_refresh_provider=lambda *args, **kwargs: {
                    'retrieved_at': now.isoformat(),
                    'rows_by_player': {'1': records[0][1]}})


def test_capture_uses_refreshed_completed_history(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from analysis.prospective_monitor import capture
    from analysis.live_benchmark import FIXTURE_ENDPOINT
    from data_sources.tff_official import BASE

    now = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    player = {'id': 1, 'name': 'P1', 'club_id': 1, 'position': 'MID',
              'price': 5, 'availability': 'AVAILABLE'}
    archive = {'source_endpoint': FIXTURE_ENDPOINT,
               'source_url': BASE + FIXTURE_ENDPOINT,
               'captured_utc': now.isoformat(),
               'weeks': {'10': {'gameweek_id': 10, 'matches': [
                            {'status': 'FT', 'homeScore': 1, 'awayScore': 0}]},
                         '12': {'gameweek_id': 12, 'deadline': '2026-11-21T09:30:00Z',
                                'matches': [{'id': 12, 'homeClubId': 1, 'awayClubId': 2,
                                    'kickoffAt': '2026-11-22T12:00:00Z',
                                    'status': 'SCHEDULED'}]}}}
    old = [{'gameweekOrder': 9, 'points': 2}]
    new = old + [{'gameweekOrder': 10, 'points': 3}]
    def generated(**kwargs):
        assert kwargs['records'][0][1] == new
        assert kwargs['history_freshness']['status'] == 'fresh'
        return {'snapshot': {'id': 'synthetic', 'captured_at': now.isoformat()},
                'predictions': [], 'variants': {}, 'data_quality': {}}
    monkeypatch.setattr('analysis.live_benchmark.generate', generated)
    result = capture(path=tmp_path/'tracking.sqlite3', fixture_archive=archive,
        players_provider=lambda: {'players': [player]},
        records_provider=lambda: [(player, old)], now=now,
        history_probe_provider=lambda *args: {'source':'official_tff_history_api',
            'retrieved_at': now.isoformat(), 'gameweek': 10,
            'available_player_ids':['1'], 'status':'available'},
        history_refresh_provider=lambda *args, **kwargs: {
            'retrieved_at': now.isoformat(), 'rows_by_player': {'1': new}})
    assert result['history_freshness']['latest_model_input_gameweek'] == 10
