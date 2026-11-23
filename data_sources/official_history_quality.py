"""Quality classification for official weekly xG/xA fields; raw rows stay intact."""
import hashlib
import json
from math import isfinite

from data_sources.provider_evidence import EvidenceValue, MissingReason

EXPECTED_FIELDS = ('xG', 'xA')


def audit_expected_metrics(rows_by_player, *, retrieved_at, source_url):
    if not source_url or not retrieved_at:
        raise ValueError('Official source URL and retrieval time required')
    rows = [row for history in rows_by_player.values() for row in history]
    active = sum((row.get('minutesPlayed') or 0) > 0 for row in rows)
    goals = sum((row.get('goals') or 0) > 0 for row in rows)
    assists = sum((row.get('assists') or 0) > 0 for row in rows)
    fields = {}
    for key in EXPECTED_FIELDS:
        values = [row.get(key) for row in rows]
        numeric = [value for value in values if isinstance(value, (int, float))
                   and not isinstance(value, bool) and isfinite(value)]
        nonzero = sum(value != 0 for value in numeric)
        unpopulated = bool(rows) and len(numeric) == len(rows) and nonzero == 0 and active > 0 and (goals + assists) > 0
        fields[key] = {'rows': len(rows), 'numeric_rows': len(numeric), 'nonzero_rows': nonzero,
                       'quality': 'suspected_unpopulated' if unpopulated else 'observed',
                       'usable': not unpopulated and len(numeric) > 0}
    return {'provider':'official_tff_history_api','source_url':source_url,
            'retrieved_at':retrieved_at,
            'rows_sha256':hashlib.sha256(json.dumps(rows_by_player, sort_keys=True,
                ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest(),
            'active_rows':active,'goal_rows':goals,
            'assist_rows':assists,'fields':fields,
            'interpretation':'All-zero fields with positive activity are quarantined as unavailable; raw values are preserved.'}


def expected_metric(row, field, quality):
    if field not in EXPECTED_FIELDS:
        raise ValueError('Unsupported expected metric')
    value = row.get(field)
    if quality['fields'][field]['quality'] == 'suspected_unpopulated':
        return EvidenceValue(field, None, field, MissingReason.UNPOPULATED_FIELD)
    if value is None:
        return EvidenceValue(field, None, field, MissingReason.NOT_REPORTED)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        return EvidenceValue(field, None, field, MissingReason.INVALID)
    return EvidenceValue(field, float(value), field)
