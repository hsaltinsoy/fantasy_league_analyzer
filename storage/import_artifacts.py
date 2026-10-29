"""Stage exact historical file bytes in PostgreSQL without altering originals."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from storage.audit import classify
from storage.db import engine_from_env
from storage.models import source_artifacts


def eligible_files(root):
    folder = root / 'historical_data'
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path.suffix.lower() in ('.json', '.csv', '.xlsx'):
            yield path


def _metadata(path, raw):
    if path.suffix.lower() != '.json':
        return {}
    try:
        parsed = json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError, ValueError):
        raise ValueError(f'Invalid JSON source: {path}') from None
    if not isinstance(parsed, dict):
        return {}
    keys = ('source_endpoint', 'source_url', 'retrieved_at', 'captured_utc',
            'collected_at', 'classification', 'evidence_quality')
    return {key: parsed[key] for key in keys if key in parsed and isinstance(parsed[key], str)}


def _timestamp(meta):
    for key in ('retrieved_at', 'captured_utc', 'collected_at'):
        raw = meta.get(key)
        if raw:
            try:
                value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                if value.tzinfo:
                    return value
            except ValueError:
                pass
    return None


def import_artifacts(root, engine):
    """One transaction; unchanged paths are no-ops, changed bytes get new versions."""
    root = Path(root).resolve()
    paths = list(eligible_files(root))
    inserted = 0
    changed_paths = []
    with engine.begin() as db:
        for path in paths:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            relative = path.relative_to(root).as_posix()
            category, _, _ = classify(path.relative_to(root))
            meta = _metadata(path, raw)
            existing = db.execute(select(source_artifacts.c.content_sha256).where(
                source_artifacts.c.source_path == relative,
                source_artifacts.c.content_sha256 == digest)).scalar_one_or_none()
            if existing is not None:
                continue
            prior = db.execute(select(source_artifacts.c.content_sha256).where(
                source_artifacts.c.source_path == relative)).first()
            if prior is not None:
                changed_paths.append(relative)
            db.execute(pg_insert(source_artifacts).values(
                source_path=relative, content_sha256=digest, format=path.suffix.lower(),
                category=category, raw_bytes=raw, imported_at=datetime.now(timezone.utc),
                source_retrieved_at=_timestamp(meta),
                source_url=meta.get('source_url') or meta.get('source_endpoint'),
                evidence_quality=meta.get('evidence_quality') or meta.get('classification'),
                metadata=meta).on_conflict_do_nothing(index_elements=['source_path', 'content_sha256']))
            inserted += 1
    return {'source_files': len(paths), 'inserted_versions': inserted,
            'already_identical': len(paths) - inserted,
            'new_versions_for_existing_paths': changed_paths}


def reconcile_artifacts(root, engine):
    root = Path(root).resolve()
    missing = []
    different = []
    paths = list(eligible_files(root))
    with engine.connect() as db:
        for path in paths:
            relative = path.relative_to(root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            found = db.execute(select(source_artifacts.c.raw_bytes).where(
                source_artifacts.c.source_path == relative,
                source_artifacts.c.content_sha256 == digest)).scalar_one_or_none()
            if found is None:
                missing.append(relative)
            elif hashlib.sha256(found).hexdigest() != digest:
                different.append(relative)
    return {'status': 'passed' if not (missing or different) else 'failed',
            'source_files': len(paths), 'exact_matches': len(paths) - len(missing) - len(different),
            'missing': missing, 'different': different}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('import', 'reconcile'))
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args()
    engine = engine_from_env()
    try:
        result = import_artifacts(args.root, engine) if args.action == 'import' else reconcile_artifacts(args.root, engine)
        print(json.dumps(result, indent=2))
        if result.get('status') == 'failed':
            raise SystemExit(2)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
