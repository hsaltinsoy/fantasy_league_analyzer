"""Lossless, repeatable SQLite tracking import and read-only reconciliation."""
import argparse
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from storage.db import engine_from_env
from storage.models import snapshots, predictions, evaluation_runs

SOURCE_TABLES = {
    'snapshots': (snapshots, ('id', 'gameweek', 'captured_at', 'deadline_at',
                             'deadline_source', 'source', 'classification', 'payload')),
    'predictions': (predictions, ('id', 'snapshot_id', 'gameweek', 'created_at', 'status',
                                 'model', 'model_version', 'risk_strategy',
                                 'raw_expected_points', 'risk_adjusted_objective', 'payload')),
    'evaluation_runs': (evaluation_runs, ('id', 'snapshot_id', 'gameweek', 'created_at',
                                         'source_digest', 'status', 'source', 'payload')),
}


def _source_hash(row):
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _time(raw):
    if raw is None:
        return None
    parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError(f'Naive timestamp in original SQLite data: {raw}')
    return parsed


def _mapped(table_name, row):
    base = dict(row)
    if table_name == 'snapshots':
        return dict(id=base['id'], gameweek=base['gameweek'],
                    captured_at_text=base['captured_at'], captured_at=_time(base['captured_at']),
                    deadline_at_text=base['deadline_at'], deadline_at=_time(base['deadline_at']),
                    deadline_source=base['deadline_source'], source_text=base['source'],
                    classification=base['classification'], payload_text=base['payload'],
                    payload=json.loads(base['payload']), source_sha256=_source_hash(base))
    if table_name == 'predictions':
        return dict(id=base['id'], snapshot_id=base['snapshot_id'], gameweek=base['gameweek'],
                    created_at_text=base['created_at'], created_at=_time(base['created_at']),
                    status=base['status'], model=base['model'], model_version=base['model_version'],
                    risk_strategy=base['risk_strategy'], raw_expected_points=base['raw_expected_points'],
                    risk_adjusted_objective=base['risk_adjusted_objective'],
                    payload_text=base['payload'], payload=json.loads(base['payload']),
                    source_sha256=_source_hash(base))
    return dict(id=base['id'], snapshot_id=base['snapshot_id'], gameweek=base['gameweek'],
                created_at_text=base['created_at'], created_at=_time(base['created_at']),
                source_digest=base['source_digest'], status=base['status'],
                source_text=base['source'], payload_text=base['payload'],
                payload=json.loads(base['payload']), source_sha256=_source_hash(base))


def _read_source(source):
    path = Path(source).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    db = sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def import_tracking(source, engine):
    """One transaction; identical IDs are no-ops and differing IDs abort."""
    summary = {}
    with _read_source(source) as old, engine.begin() as new:
        for name, (target, columns) in SOURCE_TABLES.items():
            rows = [dict(row) for row in old.execute(f'SELECT {",".join(columns)} FROM {name} ORDER BY id')]
            inserted = 0
            for row in rows:
                mapped = _mapped(name, row)
                before = new.execute(select(target.c.source_sha256).where(target.c.id == row['id'])).scalar_one_or_none()
                new.execute(pg_insert(target).values(**mapped).on_conflict_do_nothing(index_elements=['id']))
                if before is None:
                    inserted += 1
                current = new.execute(select(target.c.source_sha256).where(target.c.id == row['id'])).scalar_one()
                if current != mapped['source_sha256']:
                    raise ValueError(f'Conflicting {name} ID {row["id"]}; import rolled back')
            summary[name] = {'source': len(rows), 'inserted': inserted,
                             'already_identical': len(rows) - inserted}
    return summary


def reconcile(source, engine, *, original_gw10_snapshot='1e9f5094-9b24-42f6-a0ff-ddf201685aa8'):
    """Compare every source row and the original GW10 prediction set by content hash."""
    summary = {}
    issues = []
    with _read_source(source) as old, engine.connect() as new:
        for name, (target, columns) in SOURCE_TABLES.items():
            rows = [dict(row) for row in old.execute(f'SELECT {",".join(columns)} FROM {name} ORDER BY id')]
            dest = dict(new.execute(select(target.c.id, target.c.source_sha256)).all())
            missing = [r['id'] for r in rows if r['id'] not in dest]
            mismatched = [r['id'] for r in rows if r['id'] in dest and dest[r['id']] != _source_hash(r)]
            extra = sorted(set(dest) - {r['id'] for r in rows})
            summary[name] = {'source': len(rows), 'destination': len(dest),
                             'missing': len(missing), 'mismatched': len(mismatched), 'extra': len(extra)}
            if missing or mismatched or extra:
                issues.append(f'{name}: missing={missing}, mismatched={mismatched}, extra={extra}')
        original = old.execute('SELECT id FROM predictions WHERE snapshot_id=? ORDER BY id',
                               (original_gw10_snapshot,)).fetchall()
        pg_original = new.execute(select(predictions.c.id).where(
            predictions.c.snapshot_id == original_gw10_snapshot).order_by(predictions.c.id)).scalars().all()
        snapshot_present = new.execute(select(snapshots.c.id).where(
            snapshots.c.id == original_gw10_snapshot)).scalar_one_or_none() is not None
        summary['original_gw10'] = {'source_predictions': len(original),
                                     'destination_predictions': len(pg_original),
                                     'shared_snapshot_present': snapshot_present,
                                     'identical_ids': [r[0] for r in original] == pg_original}
        if len(original) != 11 or not snapshot_present or not summary['original_gw10']['identical_ids']:
            issues.append('Original GW10 set differs from SQLite reference')
        broken = new.execute(select(func.count()).select_from(predictions.outerjoin(
            snapshots, predictions.c.snapshot_id == snapshots.c.id)).where(snapshots.c.id.is_(None))).scalar_one()
        summary['orphan_predictions'] = broken
        if broken:
            issues.append(f'{broken} predictions lack snapshots')
    return {'status': 'passed' if not issues else 'failed', 'tables': summary, 'issues': issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('import-sqlite', 'reconcile'))
    parser.add_argument('--source', type=Path, default=Path('historical_data/prediction_tracking.sqlite3'))
    args = parser.parse_args()
    engine = engine_from_env()
    try:
        result = import_tracking(args.source, engine) if args.action == 'import-sqlite' else reconcile(args.source, engine)
        print(json.dumps(result, indent=2))
        if isinstance(result, dict) and result.get('status') == 'failed':
            raise SystemExit(2)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
