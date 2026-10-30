"""Normalize staged generated reports and declared model metadata idempotently."""
import hashlib
import json
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from storage import models as m
from storage.db import engine_from_env


def _key(prefix, *parts):
    raw = '\0'.join(map(str, parts)).encode('utf-8')
    return prefix + hashlib.sha256(raw).hexdigest()


def import_runtime_metadata(engine):
    from analysis.multiweek_backtest import MODELS
    from analysis.experimental_forecasting import NAME, BLEND, FEATURES, ALPHA, GAP_WEEKS

    inserted_reports = skipped_reports = inserted_models = skipped_models = 0
    definitions = {}
    for name, settings in MODELS.items():
        definitions[(name, 'phase6.1')] = (name != 'short_form_3w', dict(settings))
    static = {'alpha': ALPHA, 'features': list(FEATURES),
              'gap_gameweeks': GAP_WEEKS, 'chronological_training': True}
    definitions[(NAME, 'phase15.ridge-v1')] = (True, dict(static))
    definitions[(BLEND, 'phase15.ridge-v1')] = (True, {
        **static, 'blend_weights': {NAME: 0.5, 'short_form_3w': 0.5}})
    with engine.begin() as db:
        for name, version in db.execute(select(m.predictions.c.model,
                                                m.predictions.c.model_version).distinct()):
            definitions.setdefault((name, version),
                (name != 'short_form_3w', dict(MODELS.get(name, {}))))
        for (name, version), (experimental, configuration) in sorted(definitions.items()):
            existing = db.execute(select(m.forecast_models.c.id).where(
                m.forecast_models.c.name == name,
                m.forecast_models.c.version == version)).scalar_one_or_none()
            if existing is None:
                db.execute(insert(m.forecast_models).values(
                    id=_key('model:', name, version), name=name, version=version,
                    experimental=experimental, configuration=configuration))
                inserted_models += 1
            else:
                skipped_models += 1
        artifacts = db.execute(select(m.source_artifacts).where(
            m.source_artifacts.c.format.in_(('json', '.json')))).mappings().all()
        for row in artifacts:
            if 'generated' not in row['category']:
                continue
            path = row['source_path']
            digest = row['content_sha256']
            if hashlib.sha256(row['raw_bytes']).hexdigest() != digest:
                raise ValueError(f'Staged report digest mismatch: {path}')
            content = json.loads(row['raw_bytes'].decode('utf-8-sig'))
            existing = db.execute(select(m.historical_reports.c.id).where(
                m.historical_reports.c.source_path == path,
                m.historical_reports.c.content_sha256 == digest)).scalar_one_or_none()
            if existing is None:
                db.execute(insert(m.historical_reports).values(
                    id=_key('staged-report:', path, digest),
                    report_type=PurePosixPath(path).stem, source_path=path,
                    content_sha256=digest, content=content,
                    evidence_quality=row['evidence_quality'] or 'staged_generated_report',
                    imported_at=row['imported_at']))
                inserted_reports += 1
            else:
                skipped_reports += 1
    return {'models': {'inserted': inserted_models, 'skipped': skipped_models},
            'reports': {'inserted': inserted_reports, 'skipped': skipped_reports}}


def main():
    engine = engine_from_env()
    try:
        print(json.dumps(import_runtime_metadata(engine), indent=2))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
