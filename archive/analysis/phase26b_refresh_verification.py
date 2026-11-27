"""Read-only official history verification against a frozen prospective pool."""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from analysis.history_freshness import audit, latest_completed_week, require_capture_ready
from analysis.live_benchmark import _fixture_lookup, fetch_official_fixtures
from analysis.predict_next_week import predict
from analysis.prediction_tracking import get_snapshot
from data_sources.tff_official import fetch_player_histories

SNAPSHOT_ID = 'ceddd5ae-a154-411b-9581-31a484c87f5f'


def verify(snapshot_id=SNAPSHOT_ID, *, delay=.5):
    from storage.db import engine_from_env
    from storage.runtime_repository import RuntimeRepository

    snapshot = get_snapshot(snapshot_id)
    if snapshot is None:
        raise ValueError('Frozen snapshot not found')
    payload = snapshot['payload']
    players = payload['players']
    target = snapshot['gameweek']
    archive = fetch_official_fixtures()
    completed, partial = latest_completed_week(archive, target)
    if completed is None:
        raise ValueError('No completed prior week in current official fixtures')
    print(f'Starting {len(players)} sequential requests; completed through GW{completed}', flush=True)

    def progress(done, total, metrics):
        if done % 50 == 0 or done == total:
            print(f'{done}/{total} players, {metrics["requests"]} requests, '
                  f'{metrics["failed_requests"]} failures', flush=True)

    fetched = fetch_player_histories([p['id'] for p in players],
        completed_through=completed, target_week=target,
        min_interval_seconds=delay, max_retries=2,
        continue_on_error=True, include_metrics=True, progress=progress)
    rows = fetched['rows_by_player']
    staged = RuntimeRepository(engine_from_env()).historical_records(before_week=target)
    week_coverage = Counter()
    for history in rows.values():
        week_coverage.update({int(r['gameweekOrder']) for r in history})
    differences = {'new_rows': 0, 'changed_rows': 0, 'missing_staged_rows': 0}
    for pid in rows:
        new = {int(r['gameweekOrder']): r for r in rows[pid]}
        old = {int(r['gameweekOrder']): r for r in staged.get(pid, [])}
        differences['new_rows'] += len(new.keys() - old.keys())
        differences['missing_staged_rows'] += len(old.keys() - new.keys())
        differences['changed_rows'] += sum(new[w] != old[w] for w in new.keys() & old.keys())
    available = [pid for pid, history in rows.items() if any(int(r['gameweekOrder']) == completed for r in history)]
    probe = {'source': 'official_tff_history_api', 'retrieved_at': fetched['retrieved_at'],
             'source_url': fetched['source_url'], 'gameweek': completed,
             'available_player_ids': available, 'sampled_player_count': len(players),
             'status': 'available' if available else 'unavailable'}
    freshness = audit(target, players, rows, archive, source_probe=probe)
    gate = {'valid': None, 'stale': None, 'incomplete': None}
    for key, candidate in [('valid', freshness),
                           ('stale', audit(target, players, staged, archive, source_probe=probe)),
                           ('incomplete', audit(target, players, {**rows, **{pid: [] for pid in available[:70]}},
                                                archive, source_probe=probe))]:
        try:
            require_capture_ready(candidate)
            gate[key] = 'accepted'
        except ValueError as exc:
            gate[key] = str(exc)
    dry_run = {'status': 'not_run'}
    if gate['valid'] == 'accepted' and not fetched['metrics']['errors']:
        try:
            result = predict(target, players, [(p, rows[str(p['id'])]) for p in players],
                             {target: _fixture_lookup(archive['weeks'][str(target)])}, {},
                             model='short_form_3w')
            dry_run = {'status': 'in_memory_success', 'eligible_players': result['eligible_players'],
                       'formation': result['formation'], 'expected_fantasy_points': result['expected_fantasy_points']}
        except Exception as exc:
            dry_run = {'status': 'failed', 'error': str(exc)}
    return {'snapshot_id': snapshot_id, 'target_gameweek': target,
            'snapshot_player_count': len(players), 'fixture_retrieved_at': archive['captured_utc'],
            'latest_completed_gameweek': completed, 'partial_gameweeks': partial,
            'history_retrieved_at': fetched['retrieved_at'], 'metrics': fetched['metrics'],
            'filtered_week_coverage': dict(sorted(week_coverage.items())),
            'players_with_no_history': [pid for pid, history in rows.items() if not history],
            'staged_player_count': len(staged), 'staged_comparison': differences,
            'freshness': freshness, 'gate': gate, 'dry_run': dry_run,
            'target_week_leakage_count': sum(int(r['gameweekOrder']) >= target
                                              for history in rows.values() for r in history)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='docs/phase26b_refresh_verification.json')
    parser.add_argument('--delay', type=float, default=.5)
    args = parser.parse_args()
    report = verify(delay=args.delay)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
