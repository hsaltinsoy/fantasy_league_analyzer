"""Windows-friendly orchestration for immutable prospective benchmark captures."""
import argparse
import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from analysis import live_benchmark
from analysis.benchmark_evaluation import _fixture_check, evaluate_gameweek
from analysis.benchmark_verification import provenance
from analysis.prediction_tracking import DEFAULT_DB, _postgres, get_prediction, get_snapshot, latest_evaluation_run, parse_time
from analysis.production_evaluation import _metrics
from data_sources.tff_official import BASE


@contextmanager
def _capture_lock(path):
    """Serialize Windows Task Scheduler launches before checking for an existing week."""
    lock_path = Path(path).with_suffix('.capture.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as handle:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        try:
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except ImportError:  # Enables local tests on Unix too.
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def _postgres_capture_lock(repository, week_key='prospective_capture'):
    from sqlalchemy import text
    with repository.engine.connect() as db:
        db.execute(text('SELECT pg_advisory_lock(hashtextextended(:key, 0))'), {'key': week_key})
        try:
            yield
        finally:
            db.execute(text('SELECT pg_advisory_unlock(hashtextextended(:key, 0))'), {'key': week_key})


def _benchmark_snapshots(path=DEFAULT_DB, week=None):
    pg = _postgres(path)
    if pg:
        from sqlalchemy import select
        from storage import models as m
        query = (select(m.snapshots.c.id, m.snapshots.c.gameweek, m.snapshots.c.captured_at_text,
                        m.snapshots.c.deadline_at_text, m.snapshots.c.source_text,
                        m.snapshots.c.classification)
                 .join(m.predictions, m.predictions.c.snapshot_id == m.snapshots.c.id)
                 .distinct().order_by(m.snapshots.c.gameweek, m.snapshots.c.captured_at_text))
        if week is not None:
            query = query.where(m.snapshots.c.gameweek == week)
        with pg.engine.connect() as db:
            rows = db.execute(query).all()
        found = []
        for sid, gameweek, _captured, deadline, raw, classification in rows:
            source = json.loads(raw)
            predictions = [pg.get_prediction(pid) for pid in pg.prediction_ids(sid)]
            if classification == 'live' and any('benchmark' in p['payload'] for p in predictions):
                found.append({'id': sid, 'gameweek': gameweek, 'deadline': deadline, 'source': source})
        return found
    path = Path(path)
    if not path.exists():
        return []
    with sqlite3.connect(f'file:{path.resolve().as_posix()}?mode=ro', uri=True) as db:
        query = '''SELECT DISTINCT s.id,s.gameweek,s.deadline_at,s.source,s.classification
                   FROM snapshots s JOIN predictions p ON p.snapshot_id=s.id
                   WHERE (? IS NULL OR s.gameweek=?) ORDER BY s.gameweek,s.captured_at'''
        rows = db.execute(query, (week, week)).fetchall()
        found = []
        for sid, gameweek, deadline, raw, classification in rows:
            source = json.loads(raw)
            # Only the existing live benchmark schema is eligible, including original GW10.
            first = db.execute('SELECT payload FROM predictions WHERE snapshot_id=? LIMIT 1', (sid,)).fetchone()
            if classification == 'live' and first and 'benchmark' in json.loads(first[0]):
                found.append({'id':sid,'gameweek':gameweek,'deadline':deadline,'source':source})
    return found


def _existing_for_week(week, official_id, path):
    matches = [row for row in _benchmark_snapshots(path, week)
               if row['source'].get('official_gameweek_id') in (None, official_id)]
    if len(matches) > 1:
        raise ValueError('Multiple existing benchmark snapshots for gameweek; select one explicitly')
    return matches[0] if matches else None


def capture(*, path=DEFAULT_DB, fixture_archive=None, players_provider=None,
            records_provider=None, now=None, include_phase15=False):
    """Idempotently create one live benchmark set for the official next week."""
    if now is not None and now.tzinfo is None:
        raise ValueError('Capture time must include a timezone')
    pg = _postgres(path)
    lock = _capture_lock(path) if not pg else _postgres_capture_lock(pg)
    with lock:
        archive = fixture_archive if fixture_archive is not None else live_benchmark.fetch_official_fixtures()
        now = now or datetime.now(timezone.utc)
        if archive.get('source_url') != BASE+live_benchmark.FIXTURE_ENDPOINT:
            raise ValueError('Fresh official fixture API source required')
        retrieved = parse_time(archive.get('captured_utc'))
        if retrieved is None or retrieved > now or (now-retrieved).total_seconds() > 3600:
            raise ValueError('Official fixture response is stale or undated')
        week, entry = live_benchmark.next_gameweek(archive, now)
        if not isinstance(entry.get('gameweek_id'), int) or entry['gameweek_id'] < 1:
            raise ValueError('Official gameweek ID missing')
        existing = _existing_for_week(week, entry['gameweek_id'], path)
        if existing:
            return {'status':'already_captured','gameweek':week,'snapshot_id':existing['id'],
                    'deadline':existing['deadline'],'predictions_created':0}
        if _benchmark_snapshots(path, week):
            raise ValueError('Existing benchmark week has a conflicting official gameweek ID')
        deadline = parse_time(entry.get('deadline'))
        if deadline is None or now >= deadline:
            raise ValueError('Official deadline is unknown or already passed; no prediction generated')
        if players_provider is None:
            from data_sources.tff_official import fetch_players
            players_provider = fetch_players
        players_payload = players_provider()
        players = players_payload.get('players') if isinstance(players_payload, dict) else None
        if not isinstance(players, list) or not players:
            raise ValueError('Official player feed returned no players')
        player_time = datetime.now(timezone.utc).isoformat()
        records = (records_provider() if records_provider is not None else
                   None if pg else live_benchmark.load_history())
        # generate() validates the deadline again at the snapshot and every prediction INSERT.
        def create_predictions():
            result = live_benchmark.generate(fixture_archive=archive, players=players, records=records,
                path=path, now=now, strict_pre_deadline=True, players_retrieved_at=player_time)
            experimental = {'status':'not_requested'}
            if include_phase15:
                from analysis.experimental_prospective import save_variants
                if pg:
                    # An opt-in variant failure must roll back the entire PostgreSQL capture.
                    experimental = save_variants(result['snapshot']['id'], path=path)
                else:
                    try:
                        experimental = save_variants(result['snapshot']['id'], path=path)
                    except (ValueError, KeyError, OSError, TypeError) as exc:
                        experimental = {'status':'not_available','reason':str(exc)}
            return result, experimental
        if pg:
            from storage.repository import tracking_transaction
            with tracking_transaction(pg.engine):
                result, experimental = create_predictions()
        else:
            result, experimental = create_predictions()
        return {'status':'captured','gameweek':week,'gameweek_id':entry['gameweek_id'],
                'deadline':entry['deadline'],'snapshot_id':result['snapshot']['id'],
                'predictions_created':len(result['predictions']),
                'model_ids':[item['id'] for item in result['predictions']],
                'variants':result['variants'],'experimental_phase15':experimental,
                'data_quality':result['data_quality']}


def evaluate(*, gameweek=None, snapshot_id=None, path=DEFAULT_DB, fixture_archive=None,
             rows_provider=None):
    """Evaluate only after all official fixtures are complete; reuse existing scorer."""
    archive = fixture_archive if fixture_archive is not None else live_benchmark.fetch_official_fixtures()
    candidates = _benchmark_snapshots(path, gameweek)
    if snapshot_id:
        candidates = [row for row in candidates if row['id'] == snapshot_id]
    if not candidates:
        raise ValueError('No saved benchmark snapshot for selection')
    if not snapshot_id and gameweek is None:
        # Oldest complete, unevaluated week is the scheduled default.
        candidates = [row for row in candidates if latest_evaluation_run(row['id'], path) is None]
        if not candidates:
            return {'status':'nothing_pending'}
    if len(candidates) != 1:
        raise ValueError('Select --gameweek or --snapshot-id to avoid mixing snapshots')
    snapshot = get_snapshot(candidates[0]['id'], path)
    _, issues = _fixture_check(snapshot, archive)
    if issues:
        return {'status':'not_ready','gameweek':snapshot['gameweek'],'snapshot_id':snapshot['id'],
                'issues':issues,'evaluation_run_created':False}
    before = latest_evaluation_run(snapshot['id'], path)
    run = evaluate_gameweek(snapshot['id'], fixture_archive=archive, rows_provider=rows_provider, path=path)
    return {'status':run['status'],'gameweek':snapshot['gameweek'],'snapshot_id':snapshot['id'],
            'evaluation_run_id':run['id'],'evaluation_run_created':before is None or before['id']!=run['id'],
            'complete_predictions':run['payload']['complete_predictions'],
            'total_predictions':run['payload']['total_predictions'],
            'fixture_issues':run['payload']['fixture_issues'],
            'player_issues':run['payload']['player_issues']}


def report(path=DEFAULT_DB):
    """Cumulative prospective scores, separated from legacy and retrospective records."""
    rows = []
    player_errors_by_model = {}
    for item in _benchmark_snapshots(path):
        if item['source'].get('capture_kind') != 'prospective_benchmark':
            continue
        snapshot = get_snapshot(item['id'], path)
        run = latest_evaluation_run(item['id'], path)
        pg = _postgres(path)
        if pg:
            ids = pg.prediction_ids(item['id'])
        else:
            with sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro', uri=True) as db:
                ids = [row[0] for row in db.execute('SELECT id FROM predictions WHERE snapshot_id=? ORDER BY created_at,id',
                                                   (item['id'],))]
        for pid in ids:
            prediction = get_prediction(pid, path)
            if 'benchmark' not in prediction['payload']:
                continue
            evaluation = (run['payload']['prediction_results'].get(pid) if run else None) or {'status':'pending'}
            if evaluation['status']=='complete':
                player_errors_by_model.setdefault(prediction['model'],[]).extend(
                    player['error'] for player in evaluation.get('players',[]))
            evidence = provenance(prediction, snapshot)
            rows.append({'prediction_id':pid,'snapshot_id':item['id'],'gameweek':item['gameweek'],
                         'model':prediction['model'],'model_version':prediction['model_version'],
                         'verification_status':evidence['status'],
                         'independently_verified':evidence['independently_verified'],
                         'evaluation_status':evaluation['status'],
                         'predicted_points':prediction['raw_expected_points'],
                         'actual_points':evaluation.get('actual_points'),
                         'starting_xi_actual_points':evaluation.get('starting_xi_actual_points'),
                         'captain_contribution':evaluation.get('captain_contribution'),
                         'team_error':evaluation.get('error'),
                         'player_mae':(evaluation.get('player_metrics') or {}).get('mae'),
                         'xi_rank_spearman':(evaluation.get('xi_ranking') or {}).get('spearman'),
                         'source_retrieved_at':snapshot['source'].get('fixtures_retrieved_at')})
    by_model = {}
    for name in sorted({row['model'] for row in rows}):
        group = [row for row in rows if row['model']==name]
        complete = [row for row in group if row['evaluation_status']=='complete']
        errors = [row['team_error'] for row in complete]
        rank = [row['xi_rank_spearman'] for row in complete if row['xi_rank_spearman'] is not None]
        by_model[name] = {'saved':len(group),'complete':len(complete),
                          'team_metrics':_metrics(errors),
                          'player_metrics':_metrics(player_errors_by_model.get(name,[])),
                          'xi_ranking_spearman_mean':round(sum(rank)/len(rank),4) if rank else None,
                          'independently_verified':sum(row['independently_verified'] for row in group)}
    by_gameweek = {}
    for week in sorted({row['gameweek'] for row in rows}):
        subset = [row for row in rows if row['gameweek']==week]
        complete = [row for row in subset if row['evaluation_status']=='complete']
        by_gameweek[str(week)] = {'saved':len(subset),'complete':len(complete),
                                 'team_metrics':_metrics([row['team_error'] for row in complete]),
                                 'models':sorted({row['model'] for row in subset})}
    return {'classification':'prospective_local_timestamp_not_independent_proof',
            'predictions':rows,'by_model':by_model,'by_gameweek':by_gameweek,
            'gameweeks':sorted({row['gameweek'] for row in rows}),
            'limitations':['XI rank correlation uses only each selected XI, not all TFF players.',
                           'Local creation times do not independently establish pre-deadline capture.',
                           'No missing official result is assigned zero.']}


def main():
    parser = argparse.ArgumentParser(description='Official TFF prospective benchmark monitor')
    sub = parser.add_subparsers(dest='action', required=True)
    capture_cmd=sub.add_parser('capture', help='Save next official gameweek once before its deadline')
    capture_cmd.add_argument('--include-phase15', action='store_true',
                             help='Opt in to ridge and fixed blend if dated training inputs suffice')
    evaluation = sub.add_parser('evaluate', help='Score a completed saved gameweek')
    evaluation.add_argument('--gameweek', type=int)
    evaluation.add_argument('--snapshot-id')
    sub.add_parser('status', help='Read-only cumulative report')
    args = parser.parse_args()
    if args.action == 'capture':
        result = capture(include_phase15=args.include_phase15)
    elif args.action == 'evaluate':
        result = evaluate(gameweek=args.gameweek, snapshot_id=args.snapshot_id)
    else:
        result = report()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
