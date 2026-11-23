"""Resolve stale runtime player history from the official API before lineup generation."""
from datetime import datetime, timezone

from analysis.history_freshness import audit, require_capture_ready
from data_sources.tff_official import fetch_player_histories


def resolve(week, players, histories, archive, deadline, *, fetcher=fetch_player_histories,
            now=None):
    """Return verified prior-week rows and freshness evidence; never use target-week rows."""
    current = audit(week, players, histories, archive)
    if current['status'] == 'fresh':
        return histories, current
    if current['status'] not in ('source_availability_unknown', 'partial_player_coverage'):
        require_capture_ready(current)
        raise ValueError('Historical freshness gate: ' + current['status'])
    completed = current['latest_completed_gameweek']
    if completed is None:
        raise ValueError('Historical freshness gate: completed_week_unknown')
    deadline_at = datetime.fromisoformat(str(deadline).replace('Z', '+00:00'))
    if deadline_at.tzinfo is None:
        raise ValueError('Official deadline lacks timezone')
    clock = now or datetime.now(timezone.utc)
    if clock >= deadline_at:
        raise ValueError('Official deadline passed before history refresh')
    fetched = fetcher([p['id'] for p in players], completed_through=completed,
                      target_week=week, min_interval_seconds=.2, max_retries=2,
                      include_metrics=True, continue_on_error=True)
    if (not isinstance(fetched, dict) or not fetched.get('retrieved_at') or
            not isinstance(fetched.get('rows_by_player'), dict)):
        raise ValueError('Official history refresh lacks dated player rows')
    observed_at = datetime.fromisoformat(str(fetched['retrieved_at']).replace('Z', '+00:00'))
    if observed_at.tzinfo is None or observed_at >= deadline_at:
        raise ValueError('Official history arrived after lineup deadline')
    metrics = fetched.get('metrics') or {}
    if metrics.get('errors') or metrics.get('failed_requests'):
        raise ValueError('Official history refresh has failed player requests')
    rows_by_id = fetched['rows_by_player']
    ids = {str(p['id']) for p in players}
    if set(rows_by_id) != ids:
        raise ValueError('Official history refresh does not cover the player pool')
    for pid, rows in rows_by_id.items():
        if not isinstance(rows, list) or any(int(r['gameweekOrder']) >= week for r in rows):
            raise ValueError(f'Official history contains target-week or invalid rows for {pid}')
    available = [pid for pid, rows in rows_by_id.items()
                 if any(int(r['gameweekOrder']) == completed for r in rows)]
    probe = {'source': 'official_tff_history_api', 'retrieved_at': fetched['retrieved_at'],
             'source_url': fetched.get('source_url'), 'gameweek': completed,
             'available_player_ids': available, 'sampled_player_count': len(players),
             'status': 'available' if available else 'unavailable'}
    refreshed = audit(week, players, rows_by_id, archive, source_probe=probe)
    require_capture_ready(refreshed)
    if refreshed['status'] != 'fresh':
        raise ValueError('Historical freshness gate: ' + refreshed['status'])
    return rows_by_id, refreshed
