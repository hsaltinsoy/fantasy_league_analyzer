"""Runtime lineup refreshes stale history before using it for optimization."""
from datetime import datetime, timezone

import pytest

from analysis.lineup_history_refresh import resolve

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
DEADLINE = '2026-11-21T09:30:00Z'
PLAYERS = [{'id': 1}, {'id': 2}]
ARCHIVE = {'weeks': {'11': {'matches': [{'status': 'FT', 'homeScore': 1, 'awayScore': 0}]}}}
OLD = {'1': [{'gameweekOrder': 10}], '2': [{'gameweekOrder': 10}]}
FRESH = {'1': [{'gameweekOrder': 10}, {'gameweekOrder': 11}],
         '2': [{'gameweekOrder': 10}, {'gameweekOrder': 11}]}


def response(rows):
    return {'retrieved_at': NOW.isoformat(), 'source_url': 'official-history',
            'rows_by_player': rows, 'metrics': {'failed_requests': 0, 'errors': {}}}


def test_unknown_source_refreshes_full_player_pool():
    calls = []
    def fetch(ids, **kwargs):
        calls.append((ids, kwargs))
        return response(FRESH)
    histories, report = resolve(12, PLAYERS, OLD, ARCHIVE, DEADLINE,
                                fetcher=fetch, now=NOW)
    assert histories == FRESH
    assert report['status'] == 'fresh'
    assert report['players_with_up_to_date_history'] == 2
    assert calls[0][0] == [1, 2]
    assert calls[0][1]['completed_through'] == 11
    assert calls[0][1]['target_week'] == 12


def test_fresh_records_do_not_call_api():
    rows, report = resolve(12, PLAYERS, FRESH, ARCHIVE, DEADLINE,
        fetcher=lambda *args, **kwargs: pytest.fail('unnecessary API call'), now=NOW)
    assert rows == FRESH and report['status'] == 'fresh'


@pytest.mark.parametrize('rows,match', [
    ({'1': FRESH['1']}, 'cover the player pool'),
    ({'1': FRESH['1'], '2': OLD['2']}, 'partial_player_coverage'),
    ({'1': FRESH['1'], '2': FRESH['2'] + [{'gameweekOrder': 12}]}, 'target-week'),
])
def test_incomplete_or_future_history_is_rejected(rows, match):
    with pytest.raises(ValueError, match=match):
        resolve(12, PLAYERS, OLD, ARCHIVE, DEADLINE,
                fetcher=lambda *args, **kwargs: response(rows), now=NOW)


def test_deadline_rechecked_after_refresh():
    late = response(FRESH)
    late['retrieved_at'] = DEADLINE
    with pytest.raises(ValueError, match='after lineup deadline'):
        resolve(12, PLAYERS, OLD, ARCHIVE, DEADLINE,
                fetcher=lambda *args, **kwargs: late, now=NOW)
