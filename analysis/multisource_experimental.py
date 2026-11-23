"""Opt-in, point-in-time feature overlay. No production prediction writes."""
from datetime import datetime, timezone


def evidence(provider, entity_type, provider_id, values, fetched_at, match_at=None,
             canonical_id=None, confidence=None):
    """Keep source identifiers and raw values alongside optional verified mappings."""
    stamp = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Fetch timestamp must include a timezone')
    if entity_type not in ('player', 'team', 'match'):
        raise ValueError('Unknown entity type')
    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError('Confidence must be between zero and one')
    return {'provider': provider, 'entity_type': entity_type,
            'provider_id': str(provider_id), 'canonical_id': canonical_id,
            'match_at': match_at, 'fetched_at': stamp.astimezone(timezone.utc).isoformat(),
            'confidence': confidence, 'values': dict(values)}


def rest_days_adjustment(player, team_features, fixture_date, weight=0.0):
    """Experimental rest signal; a zero default preserves baseline projections."""
    if not 0 <= weight <= .1:
        raise ValueError('Rest weight must be in [0, 0.1]')
    last = team_features.get('last_match_date')
    if last is None or fixture_date is None:
        return {**player, 'rest_days': None, 'rest_adjustment': None}
    from datetime import date
    days = (date.fromisoformat(str(fixture_date)[:10]) - date.fromisoformat(str(last)[:10])).days
    if days < 0:
        raise ValueError('Fixture precedes latest feature match; future-data leakage')
    # Short recovery is a hypothesis, not a calibrated coefficient.
    fraction = -weight if days < 3 else 0.0
    return {**player, 'rest_days': days, 'rest_adjustment': fraction,
            'baseline_xpts': player['xpts'],
            'xpts': round(max(.1, player['xpts'] * (1 + fraction)), 3)}
