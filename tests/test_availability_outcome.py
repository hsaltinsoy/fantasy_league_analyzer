from datetime import datetime, timezone

from analysis import availability_outcome as ao


def player(pid, status=None, pct=None):
    return {'id': pid, 'availability': status, 'availability_percent': pct}


def test_status_buckets():
    assert ao.status_bucket(player(1)) == 'unknown'
    assert ao.status_bucket(player(1, 'UNKNOWN')) == 'unknown'
    assert ao.status_bucket(player(1, 'AVAILABLE', 100)) == 'clear'
    assert ao.status_bucket(player(1, 'DOUBTFUL', 50)) == 'percent_26_50'
    assert ao.status_bucket(player(1, 'DOUBTFUL', 75)) == 'percent_51_75'
    assert ao.status_bucket(player(1, 'DOUBTFUL', 90)) == 'percent_76_99'
    assert ao.status_bucket(player(1, 'UNAVAILABLE', 0)) == 'percent_0_25'
    assert ao.status_bucket(player(1, 'SUSPENDED')) == 'flagged_suspended'


def test_week_minutes_ignores_other_weeks_and_missing_rows():
    histories = [{'player_id': 1, 'rows': [{'gameweekOrder': 11, 'minutesPlayed': 90},
                                            {'gameweekOrder': 12, 'minutesPlayed': 0}]},
                 {'player_id': 2, 'rows': [{'gameweekOrder': 11, 'minutesPlayed': 45}]}]
    assert ao.week_minutes(histories, 12) == {'1': 0.0}


def test_evaluate_recall_and_precision():
    players = [player(1, 'AVAILABLE', 100), player(2, 'DOUBTFUL', 50), player(3, 'UNAVAILABLE', 0),
               player(4, 'AVAILABLE', 100), player(5), player(6, 'DOUBTFUL', 75)]
    minutes = {'1': 90, '2': 0, '3': 0, '4': 0, '5': 30}  # player 6 has no outcome row
    report = ao.evaluate(12, players, minutes)
    assert report['players_compared'] == 5
    assert report['players_without_outcome_row'] == 1
    assert report['zero_minute_players'] == 3
    assert report['zero_minute_players_that_were_flagged'] == 2
    assert report['recall_of_zero_minutes_pct'] == 66.7
    assert report['flagged_players'] == 2 and report['flagged_players_who_played'] == 0
    assert report['precision_of_flag_pct'] == 100.0
    assert report['by_bucket']['clear'] == {'n': 2, 'played': 1, 'zero_minutes': 1, 'played_pct': 50.0,
                                            'played_60plus_pct': 50.0, 'mean_minutes': 45.0}


def snap(sid, week, captured, deadline, histories=None):
    t = lambda h: datetime(2026, 11, 20, h, tzinfo=timezone.utc)
    return {'id': sid, 'week': week, 'captured_at': t(captured), 'deadline_at': t(deadline) if deadline else None,
            'classification': 'x', 'payload': {'players': [], 'histories': histories or []}}


def test_snapshot_selection_uses_latest_pre_deadline_and_later_week_outcome():
    rows = [{'player_id': 1, 'rows': [{'gameweekOrder': 12, 'minutesPlayed': 90}]}]
    snaps = [snap('early', 12, 8, 16), snap('late', 12, 14, 16), snap('post', 12, 17, 16),
             snap('next-empty', 13, 9, 20), snap('next', 13, 10, 20, rows)]
    assert ao.pick_status_snapshot(snaps, 12)['id'] == 'late'
    assert ao.pick_outcome_snapshot(snaps, 12)['id'] == 'next'
    assert ao.pick_outcome_snapshot(snaps, 13) is None


def test_regular_ids_need_two_of_last_three_60_minute_games():
    def h(pid, mins):
        return {'player_id': pid, 'rows': [{'gameweekOrder': i + 1, 'minutesPlayed': m} for i, m in enumerate(mins)]}
    histories = [h(1, [90, 90, 90]), h(2, [90, 20, 80]), h(3, [90, 20, 30]), h(4, [0, 0, 90]),
                 h(5, [90, 90, 90, 90]), h(6, [90])]
    # week 4: rows with gameweekOrder >= 4 must be ignored, so player 5 uses weeks 1-3
    assert ao.regular_ids(histories, 4) == {'1', '2', '5'}


def test_evaluate_regulars_segment():
    players = [player(1, 'AVAILABLE', 100), player(2, 'SUSPENDED'), player(3, 'AVAILABLE', 100)]
    minutes = {'1': 0, '2': 0, '3': 0}
    report = ao.evaluate(12, players, minutes, regulars={'1', '2'})
    reg = report['regulars']
    assert reg['players_compared'] == 2
    assert reg['zero_minute_players'] == 2
    assert reg['zero_minute_players_that_were_flagged'] == 1
    assert reg['recall_of_zero_minutes_pct'] == 50.0
    assert 'regulars' not in reg
    assert report['players_compared'] == 3
