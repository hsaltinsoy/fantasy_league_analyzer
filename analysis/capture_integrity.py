"""Point-in-time capture validation shared by prospective workflows."""
import hashlib
import json
from datetime import datetime, timezone


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), default=str).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def classify(captured_at, deadline_at, deadline_source, observations=None):
    def utc(value):
        if value is None:
            return None
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('Timestamp lacks timezone')
        return parsed.astimezone(timezone.utc)
    capture, deadline = utc(captured_at), utc(deadline_at)
    if capture is None:
        raise ValueError('Capture timestamp required')
    if deadline is None or not deadline_source:
        return 'unknown_deadline'
    if capture >= deadline:
        return 'post_deadline'
    for source, observed in (observations or {}).items():
        stamp = utc(observed)
        if stamp is None or stamp > capture or stamp >= deadline:
            raise ValueError(f'Invalid source observation time: {source}')
    # Local timestamps cannot prove the capture happened before a real deadline.
    return 'local_pre_deadline_unverified'


def validate_inputs(week, players, fixtures, histories):
    if not players or not fixtures or len(histories) != len(players):
        raise ValueError('Complete candidate pool, fixtures and histories required')
    ids = [str(p.get('id')) for p in players]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate candidate player ID')
    if {str(h.get('player_id')) for h in histories} != set(ids):
        raise ValueError('Historical records do not cover candidate pool')
    for p in players:
        if any(p.get(key) is None for key in ('id', 'name', 'position', 'price')) or \
                (p.get('club_id') is None and p.get('team') is None):
            raise ValueError('Candidate identity, club, position or price missing')
    for item in histories:
        for row in item.get('rows') or []:
            if int(row['gameweekOrder']) >= week:
                raise ValueError('Future fantasy statistics in candidate history')
    return digest({'week': week, 'players': players, 'fixtures': fixtures, 'histories': histories})
