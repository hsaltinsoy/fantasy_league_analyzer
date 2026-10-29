"""Conservative matchday availability gates; no inferred disciplinary bans."""
from datetime import date

BLOCKED = {'UNAVAILABLE', 'SUSPENDED', 'INJURED', 'OUT', 'BANNED'}
DOUBTFUL = {'DOUBTFUL', 'QUESTIONABLE', 'DOUBT', 'INJURY_DOUBT'}

def evaluate(player, overrides=None, round_number=10, today=None):
    """Return availability decision for a TFF player.

    Manual overrides are scoped to a specific round and must carry a source.
    Unknown official statuses are not treated as confirmed healthy.
    """
    today = today or date.today()
    overrides = overrides or []
    pid = str(player.get('id'))
    applicable = [r for r in overrides if str(r.get('player_id')) == pid and r.get('round') == round_number
                  and r.get('source') and r.get('status') in ('OUT', 'DOUBTFUL', 'AVAILABLE')
                  and (not r.get('expires') or date.fromisoformat(r['expires']) >= today)]
    if str(player.get('availability') or '').upper() in BLOCKED:
        return {'eligible': False, 'factor': 0, 'status': str(player['availability']).upper(), 'source': 'TFF API', 'checked_at': None}
    if applicable:
        r = applicable[-1]
        status = r['status']
        return {'eligible': status != 'OUT', 'factor': 0 if status == 'OUT' else (0.5 if status == 'DOUBTFUL' else 1),
                'status': status, 'source': r['source'], 'checked_at': r.get('checked_at')}
    raw = str(player.get('availability') or '').upper()
    if raw in BLOCKED:
        return {'eligible': False, 'factor': 0, 'status': raw, 'source': 'TFF API', 'checked_at': None}
    percent = player.get('availability_percent')
    try:
        factor = max(0, min(1, float(percent)/100)) if percent is not None else (0.5 if raw in DOUBTFUL else 1)
    except (TypeError, ValueError):
        factor = 0.5 if raw in DOUBTFUL else 1
    return {'eligible': factor > 0, 'factor': factor, 'status': raw or 'UNKNOWN',
            'source': 'TFF API' if raw or percent is not None else 'Bilinmiyor', 'checked_at': None}
