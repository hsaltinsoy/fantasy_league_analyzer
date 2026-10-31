"""Stable fingerprints for equivalent forecast inputs across API and reports."""
import hashlib
import json
from sqlalchemy import select
from storage import models as m


def fingerprint(week, players, histories, fixture_entry, model, risk_profile, tow_weight):
    payload = {'week': week, 'players': players, 'histories': histories,
               'fixtures': fixture_entry, 'model': model,
               'risk_profile': risk_profile, 'tow_weight': float(tow_weight)}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def source_versions(engine):
    result = {}
    with engine.connect() as db:
        for kind, prefix in (('players', 'tff-current-%'), ('fixtures', 'tff-fixtures-%')):
            row = db.execute(select(m.source_payloads.c.id,
                m.source_payloads.c.retrieved_at,
                m.source_payloads.c.content_sha256).where(
                m.source_payloads.c.id.like(prefix)).order_by(
                m.source_payloads.c.retrieved_at.desc()).limit(1)).first()
            if row is None:
                raise ValueError(f'No {kind} source version available')
            result[kind] = {'id': row.id, 'retrieved_at': row.retrieved_at.isoformat(),
                            'sha256': row.content_sha256}
    return result
