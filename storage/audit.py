"""Generate a metadata-only inventory; never reads or prints secret values."""
import argparse
import csv
import json
from pathlib import Path


def classify(path):
    name = path.name
    parts = path.parts
    if name == 'prediction_tracking.sqlite3':
        return 'persistent application data', 'snapshots / predictions / evaluation_runs', 'prediction_tracking; Flask; benchmark; prospective_monitor'
    if name == 'players.json':
        return 'persistent current player data', 'players / player_state', 'Flask /lineup; live_benchmark; official ingestion'
    if name.startswith('player_') and name.endswith('.json') and name[7:-5].isdigit():
        return 'historical player data', 'player_gameweek_stats / source_payloads', 'historical backtests; forecast feature builders'
    if 'raw' in parts and 'recovered' in parts:
        return 'immutable historical evidence', 'source_payloads / collection_runs', 'historical_recovery; recovered_history; ranking evaluation'
    if 'snapshots' in parts and 'recovered' in parts:
        return 'retrospective reconstruction', 'source_payloads / player_state', 'historical_recovery; historical evaluation'
    if 'derived' in parts and 'recovered' in parts:
        return 'derived historical evidence', 'source_payloads / player_state', 'historical_recovery; historical evaluation'
    if name.endswith('.lock'):
        return 'temporary lock', 'none', 'prospective_monitor'
    if 'example' in name or 'examples' in parts or 'template' in name:
        return 'source-controlled example', 'none', 'documentation; tests'
    if name.endswith('.sqlite3'):
        return 'persistent application data', 'manual review', 'manual review'
    if name in ('club_metadata.json', 'club_id_mapping_candidates.json'):
        return 'reference/cache', 'teams / identity mappings / source_payloads', 'club metadata; fixture validation'
    if 'fixture' in name or name.startswith('next_week_'):
        return 'fixture evidence or generated lineup', 'fixtures / historical_reports / predictions', 'Flask; dashboard; fixture ingestion'
    if 'manifest' in name or 'coverage' in name:
        return 'evidence manifest or generated coverage', 'collection_runs / historical_reports', 'historical_recovery; Flask benchmark'
    if path.suffix in ('.csv', '.xlsx'):
        return 'historical evidence or generated export', 'historical_reports / source_payloads', 'historical evaluation; exports'
    if path.suffix == '.json':
        return 'generated report or reference data', 'historical_reports / source_payloads', 'Flask benchmark; analysis scripts'
    return 'documentation', 'none', 'developers'


def shape(path):
    if path.suffix == '.json':
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            return f'{len(payload)} top-level entries' if isinstance(payload, (list, dict)) else 'scalar'
        except (ValueError, UnicodeError):
            return 'unreadable JSON'
    if path.suffix == '.csv':
        try:
            with path.open(encoding='utf-8-sig', newline='') as handle:
                return f'{sum(1 for _ in csv.reader(handle)) - 1} data rows'
        except (UnicodeError, ValueError):
            return 'unreadable CSV'
    return 'not counted'


def inventory(root):
    roots = [root / 'historical_data', root / 'examples', root / 'data_sources' / 'examples']
    files = [path for directory in roots if directory.exists() for path in directory.rglob('*') if path.is_file()]
    files.extend(path for path in root.glob('tff_*.json') if path.is_file())
    files.extend(path for path in root.glob('*.example.json') if path.is_file())
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def write_manifest(root, output):
    rows = []
    for path in inventory(root):
        relative = path.relative_to(root)
        category, destination, consumers = classify(relative)
        rows.append((relative.as_posix(), path.suffix or '(none)', path.stat().st_size,
                     shape(path), category, consumers, destination))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8') as handle:
        handle.write('# Phase 17 per-file storage inventory\n\n')
        handle.write('Top-level JSON entries are a shape count, not necessarily a player or match count. '
                     'No file contents are included. See `phase17_storage_audit.md` for migration risks.\n\n')
        handle.write('| Path | Format | Bytes | Count | Class | Consumers/writers | Destination |\n')
        handle.write('|---|---|---:|---|---|---|---|\n')
        for row in rows:
            handle.write('| ' + ' | '.join(str(value).replace('|', '\\|') for value in row) + ' |\n')
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, default=Path('docs/phase17_storage_manifest.md'))
    args = parser.parse_args()
    print(f'Inventoried {write_manifest(args.root.resolve(), args.output.resolve())} files')
