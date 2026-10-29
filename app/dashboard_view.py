"""Read-only presentation data for the integrated dashboard."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from analysis.prediction_tracking import DEFAULT_DB, get_prediction, get_snapshot


STORE = Path('historical_data')


def next_gameweek(store=STORE, now=None):
    """Use the archived official fixture deadlines, never a hard-coded week."""
    path = Path(store) / 'tff_fixtures_verified_v5.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Current time must include a timezone')
    candidates = []
    for key, week in data.get('weeks', {}).items():
        try:
            deadline = datetime.fromisoformat(week['deadline'].replace('Z', '+00:00'))
            number = int(key)
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        if deadline > now and week.get('matches'):
            candidates.append((deadline, number, week))
    if not candidates:
        return None
    deadline, number, week = min(candidates)
    return {'number': number, 'id': week.get('gameweek_id'),
            'deadline': deadline.isoformat(), 'fixtures': len(week['matches']),
            'source': data.get('source_endpoint'), 'source_captured_at': data.get('captured_utc')}


def dashboard_data(store=STORE, *, now=None, prediction_path=None):
    store = Path(store)
    upcoming = next_gameweek(store, now)
    cached = None
    prediction = None
    snapshot = None
    provenance = None
    if upcoming:
        path = store / f"next_week_gw{upcoming['number']}.json"
        if path.exists():
            try:
                candidate = json.loads(path.read_text(encoding='utf-8'))
                if candidate.get('week') == upcoming['number'] and len(candidate.get('starting_xi', [])) == 11:
                    cached = candidate
                    tracking = cached.get('prediction_tracking') or {}
                    if tracking.get('id') and Path(prediction_path or DEFAULT_DB).exists():
                        kwargs = {'path': prediction_path} if prediction_path is not None else {}
                        try:
                            prediction = get_prediction(tracking['id'], **kwargs)
                            if prediction and prediction['snapshot_id'] == tracking.get('snapshot_id'):
                                snapshot = get_snapshot(prediction['snapshot_id'], **kwargs)
                                if snapshot:
                                    from analysis.benchmark_verification import provenance as inspect_provenance
                                    provenance = inspect_provenance(prediction, snapshot)
                            else:
                                prediction = None
                        except (sqlite3.DatabaseError, OSError, ValueError):
                            prediction = None
                            snapshot = None
            except (OSError, ValueError, TypeError, KeyError):
                cached = None
    return {'upcoming': upcoming, 'lineup': cached, 'prediction': prediction,
            'snapshot': snapshot, 'provenance': provenance}
