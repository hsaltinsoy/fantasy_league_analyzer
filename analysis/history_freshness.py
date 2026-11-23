"""Point-in-time history freshness audit for prospective captures."""
from collections import Counter

FINISHED = {'FT', 'FINISHED', 'COMPLETED'}


def latest_completed_week(archive, target_week):
    completed = []
    partial = []
    for key, entry in (archive.get('weeks') or {}).items():
        week = int(key)
        if week >= target_week:
            continue
        matches = entry.get('matches') or []
        if matches and all(str(m.get('status') or '').upper() in FINISHED and
                           m.get('homeScore') is not None and m.get('awayScore') is not None
                           for m in matches):
            completed.append(week)
        elif matches:
            partial.append(week)
    return max(completed, default=None), sorted(partial)


def audit(target_week, players, histories, archive, *, source_probe=None,
          allow_source_unavailable=False):
    """Separate fixture completion, observed source availability and stored history."""
    completed, partial = latest_completed_week(archive, target_week)
    by_id = {str(p['id']): histories.get(str(p['id']), []) for p in players}
    weeks = []
    for rows in by_id.values():
        for row in rows:
            week = int(row['gameweekOrder'])
            if week >= target_week:
                raise ValueError('Target-week or future history in pre-capture inputs')
            weeks.append(week)
    latest = max(weeks, default=None)
    used = min(latest, completed) if latest is not None and completed is not None else latest
    current = sum(any(int(r['gameweekOrder']) == completed for r in rows)
                  for rows in by_id.values()) if completed is not None else 0
    probe = source_probe or {}
    observed = probe.get('available_player_ids') or []
    source_latest = probe.get('gameweek') if observed else None
    if source_latest is not None and (source_latest >= target_week or
                                     not probe.get('retrieved_at') or
                                     probe.get('source') != 'official_tff_history_api'):
        raise ValueError('Invalid official history availability evidence')
    missing = (list(range((latest or 0)+1, completed+1))
               if completed is not None and (latest or 0) < completed else [])
    reasons = []
    if latest is None:
        reasons.append('no_stored_player_history')
    if missing:
        reasons.append('stored_history_behind_completed_fixtures')
    if partial:
        reasons.append('partial_gameweeks_not_required')
    if completed is not None and latest is not None and latest > completed:
        status = 'unfinalized_history_present'
        reasons.append('history_contains_unfinalized_gameweek')
    elif missing and source_latest is not None and source_latest >= min(missing):
        status = 'confirmed_ingestion_failure'
    elif (missing and probe.get('status') == 'unavailable' and probe.get('retrieved_at')
          and probe.get('source') == 'official_tff_history_api'
          and probe.get('sampled_player_count') == len(players)):
        status = 'source_unavailable' if allow_source_unavailable else 'source_unavailable_requires_override'
    elif missing:
        status = 'source_availability_unknown'
    elif completed is None:
        status = 'completed_week_unknown'
    else:
        status = 'fresh' if current / max(1, len(players)) >= .9 else 'partial_player_coverage'
    return {'target_gameweek': target_week, 'latest_completed_gameweek': completed,
            'partial_gameweeks': partial, 'latest_available_historical_gameweek': source_latest,
            'latest_stored_historical_gameweek': latest,
            'latest_model_input_gameweek': used,
            'players_with_up_to_date_history': current,
            'player_count': len(players),
            'up_to_date_percentage': round(100*current/len(players), 2) if players else None,
            'missing_gameweeks': missing,
            'fixture_source_retrieved_at': archive.get('captured_utc'),
            'history_source_retrieved_at': probe.get('retrieved_at'),
            'history_source_url': probe.get('source_url'),
            'status': status, 'reasons': reasons}


def require_capture_ready(report):
    if report['status'] in ('confirmed_ingestion_failure',
                            'source_unavailable_requires_override',
                            'source_availability_unknown', 'partial_player_coverage',
                            'unfinalized_history_present'):
        raise ValueError('Historical freshness gate: ' + report['status'])
