"""Conservative GW1–GW9 evaluation using explicit, point-in-time input bundles.

The existing player archive contains outcomes, not historical eligibility snapshots.
Never infer an input pool from those outcomes or from today's players.json.
"""
import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from analysis.benchmark_evaluation import _actual_check, _fixture_check
from analysis.multiweek_backtest import MODELS
from analysis.prediction_tracking import parse_time
from analysis.production_evaluation import _metrics, evaluate_saved
from analysis.predict_next_week import predict

STORE = Path('historical_data')
SNAPSHOT_DIR = STORE / 'walkforward_snapshots'
REPORT_DIR = STORE / 'walkforward_phase10'
MODEL_NAMES = (*MODELS, 'dashboard_tff_xgedge', 'experimental_covariance',
               'experimental_appearance', 'experimental_direct_risk')
POSITION_SET = {'GK', 'DEF', 'MID', 'FWD'}


def _strict_inputs(snapshot, week):
    """Reject unknown or later-week eligibility instead of borrowing current values."""
    if snapshot.get('gameweek') != week or snapshot.get('classification') not in ('live', 'historical_reconstruction'):
        raise ValueError('missing_or_inconsistent_week_snapshot')
    captured, deadline = parse_time(snapshot.get('captured_at')), parse_time(snapshot.get('deadline_at'))
    if captured is None or deadline is None or captured >= deadline:
        raise ValueError('no_predeadline_input_capture')
    payload = snapshot.get('payload') or {}
    players, fixtures, histories = (payload.get(k) for k in ('players', 'fixtures', 'histories'))
    if not all(isinstance(v, list) and v for v in (players, fixtures, histories)):
        raise ValueError('missing_historical_players_fixtures_or_histories')
    ids = []
    for player in players:
        if not isinstance(player, dict) or any(player.get(k) is None for k in
                                               ('id', 'name', 'position', 'price', 'availability')):
            raise ValueError('missing_historical_player_field')
        club = player.get('club_id') or player.get('team')
        if club is None or player['position'] not in POSITION_SET or \
           isinstance(player['price'], bool) or not isinstance(player['price'], (int, float)) or \
           not math.isfinite(player['price']) or player['price'] <= 0:
            raise ValueError('missing_or_invalid_historical_club_position_price')
        ids.append(str(player['id']))
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate_historical_player_id')
    fixture_map = {}
    for fixture in fixtures:
        home, away, fid = (fixture.get(k) for k in ('homeClubId', 'awayClubId', 'id'))
        if fid is None or home is None or away is None or str(home) == str(away):
            raise ValueError('invalid_historical_fixture')
        if str(home) in fixture_map or str(away) in fixture_map:
            raise ValueError('duplicate_historical_fixture_club')
        fixture_map[str(home)], fixture_map[str(away)] = str(away), str(home)
    if any(str(p.get('club_id') or p.get('team')) not in fixture_map for p in players):
        raise ValueError('player_club_missing_from_historical_fixture')
    seen = set()
    for history in histories:
        pid = str(history.get('player_id'))
        if pid not in ids or pid in seen or not isinstance(history.get('rows'), list):
            raise ValueError('invalid_historical_history_identity')
        seen.add(pid)
        for row in history['rows']:
            try:
                order = int(row['gameweekOrder'])
            except (KeyError, TypeError, ValueError):
                raise ValueError('invalid_historical_history_week') from None
            if order >= week:
                raise ValueError('future_statistics_in_input_snapshot')
    if seen != set(ids):
        raise ValueError('missing_historical_player_history')
    return players, histories, fixtures, fixture_map


def _local_actuals(store, week, selected_ids):
    """Outcome archive only; local files are not independent official receipts."""
    rows = {}
    for pid in selected_ids:
        path = Path(store) / f'player_{pid}.json'
        if not path.exists():
            rows[str(pid)] = []
            continue
        history = json.loads(path.read_text(encoding='utf-8'))
        rows[str(pid)] = [r for r in history if isinstance(r, dict) and
                          str(r.get('gameweekOrder')) == str(week)]
    return {'source_url': 'local_archive:' + str(store),
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'rows_by_player': rows, 'provenance': 'local_archive_not_independently_verified'}


def _validate_lineup(result, players):
    from analysis.optimizer import FORMATIONS
    xi, bench = result.get('starting_xi') or [], result.get('bench') or []
    if len(xi) != 11 or len(bench) != 4 or sum(bool(p.get('captain')) for p in xi) != 1:
        raise ValueError('incomplete_starting_xi_bench_or_captain')
    selected = xi + bench
    ids = [str(p.get('id')) for p in selected]
    source = {str(p['id']): p for p in players}
    if len(set(ids)) != 15 or any(pid not in source for pid in ids):
        raise ValueError('duplicate_or_unknown_squad_player')
    for p in selected:
        original = source[str(p['id'])]
        if p.get('position') != original['position'] or \
           str(p.get('team')) != str(original.get('club_id') or original.get('team')) or \
           p.get('price') != original['price']:
            raise ValueError('selected_player_identity_or_price_mismatch')
    positions = Counter(p['position'] for p in selected)
    if positions != {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}:
        raise ValueError('invalid_squad_positions')
    starts = Counter(p['position'] for p in xi)
    if starts['GK'] != 1 or tuple(starts[pos] for pos in ('DEF', 'MID', 'FWD')) not in FORMATIONS:
        raise ValueError('invalid_starting_formation')
    clubs = Counter(str(p['team']) for p in selected)
    if max(clubs.values()) > 3 or sum(p['price'] for p in selected) > 100 + 1e-8:
        raise ValueError('club_or_budget_limit_exceeded')


def evaluate_week(snapshot, fixture_archive, actual_provider, *, models=MODELS, predictor=predict):
    """All models receive the same frozen input; actuals are loaded only after prediction."""
    week = snapshot['gameweek']
    players, histories, _, fixture_map = _strict_inputs(snapshot, week)
    entry, fixture_issues = _fixture_check(snapshot, fixture_archive)
    if fixture_issues:
        raise ValueError('official_fixture_validation:' + ','.join(fixture_issues))
    records = [(p, next(h['rows'] for h in histories if str(h['player_id']) == str(p['id'])))
               for p in players]
    outcomes = {}
    for model in models:
        try:
            result = predictor(week, players, records, {week: fixture_map}, {}, model=model)
            _validate_lineup(result, players)
            outcomes[model] = result
        except (ValueError, KeyError, RuntimeError) as exc:
            outcomes[model] = {'error': str(exc)}
    selected_ids = {str(p['id']) for result in outcomes.values() if 'error' not in result
                    for p in result['starting_xi']}
    if not selected_ids:
        return {'week': week, 'classification': 'not_evaluable', 'models':
                {name: {'status': 'not_evaluable', 'reason': value['error']}
                 for name, value in outcomes.items()}}
    fetched = actual_provider(week, selected_ids)
    actual, actual_issues = _actual_check(
        snapshot, entry, fetched, selected_ids,
        allow_local_archive=fetched.get('provenance') == 'local_archive_not_independently_verified')
    results = {}
    for model, result in outcomes.items():
        if 'error' in result:
            results[model] = {'status': 'not_evaluable', 'reason': result['error']}
            continue
        prediction = {'id': f'retrospective-gw{week}-{model}', 'gameweek': week,
                      'status': 'retrospective_reconstruction', 'model': model,
                      'risk_adjusted_objective': result.get('risk_adjusted_objective'),
                      'payload': result}
        scored = evaluate_saved(prediction, snapshot['payload'], actual)
        if 'actual_points' not in scored:
            scored = {**scored, 'status': 'not_evaluable',
                      'player_issues': {str(p['id']): actual_issues[str(p['id'])]
                                        for p in result['starting_xi'] if str(p['id']) in actual_issues}}
        else:
            scored['status'] = 'retrospective_reconstruction'
            scored['classification'] = 'retrospective_reconstruction'
        results[model] = scored
    classification = ('retrospective_reconstruction' if any(
        row['status'] == 'retrospective_reconstruction' for row in results.values())
        else 'not_evaluable')
    return {'week': week, 'classification': classification,
            'snapshot_id': snapshot.get('id'), 'actuals_provenance': fetched.get('provenance'),
            'actual_player_coverage': len(actual) / len(selected_ids),
            'models': results}


def audit_coverage(store=STORE, snapshot_dir=SNAPSHOT_DIR):
    store, snapshot_dir = Path(store), Path(snapshot_dir)
    players_path = store / 'players.json'
    player_count = len(json.loads(players_path.read_text(encoding='utf-8'))) if players_path.exists() else 0
    files = list(store.glob('player_*.json'))
    weeks = {week: {'week': week, 'history_rows': 0, 'prior_history_players': 0,
                    'prior_positive_price_players': 0, 'target_result_rows': 0,
                    'target_result_rows_with_points': 0, 'historical_club_fields': 0,
                    'historical_position_fields': 0, 'historical_status_fields': 0}
             for week in range(1, 10)}
    for path in files:
        rows = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(rows, list):
            continue
        for week, item in weeks.items():
            past = [r for r in rows if isinstance(r, dict) and isinstance(r.get('gameweekOrder'), int)
                    and r['gameweekOrder'] < week]
            target = [r for r in rows if isinstance(r, dict) and r.get('gameweekOrder') == week]
            item['history_rows'] += len(past)
            item['prior_history_players'] += bool(past)
            item['prior_positive_price_players'] += bool(past and any(
                isinstance(r.get('cost'), (int, float)) and not isinstance(r.get('cost'), bool)
                and r['cost'] > 0 for r in past))
            item['target_result_rows'] += len(target)
            item['target_result_rows_with_points'] += sum(r.get('points') is not None for r in target)
            item['historical_club_fields'] += sum('clubId' in r or 'teamId' in r for r in target)
            item['historical_position_fields'] += sum('position' in r for r in target)
            item['historical_status_fields'] += sum('availability' in r or 'status' in r for r in target)
    archive_path = store / 'tff_fixtures_verified_v5.json'
    archive = json.loads(archive_path.read_text(encoding='utf-8')) if archive_path.exists() else {}
    for week, item in weeks.items():
        entry = (archive.get('weeks') or {}).get(str(week)) or {}
        item['official_fixture_count'] = len(entry.get('matches') or [])
        item['official_deadline'] = entry.get('deadline')
        snapshot_path = snapshot_dir / f'gw{week}.json'
        item['input_snapshot_path'] = str(snapshot_path) if snapshot_path.exists() else None
        item['classification'] = 'not_evaluable'
        item['reason'] = ('no_preseason_history' if week == 1 else
                          'no_complete_predeadline_historical_eligibility_snapshot')
    return {'classification': 'historical_data_audit', 'current_player_catalog_count': player_count,
            'history_file_count': len(files), 'weeks': list(weeks.values()),
            'model_eligibility': {name: 'not_evaluable_without_complete_weekly_input_snapshot'
                                  for name in MODEL_NAMES},
            'limitations': ['Current players.json cannot establish historical clubs, positions, prices or availability.',
                            'Prior match cost is not a verified target-week deadline price.',
                            'Historical player rows contain no club, position or availability fields.',
                            'No independent predeadline timestamp proof is available for GW1-GW9.']}


def run(store=STORE, snapshot_dir=SNAPSHOT_DIR, *, predictor=predict):
    """Chronological report; missing snapshots remain explicit non-evaluable rows."""
    store, snapshot_dir = Path(store), Path(snapshot_dir)
    report = audit_coverage(store, snapshot_dir)
    archive_path = store / 'tff_fixtures_verified_v5.json'
    archive = json.loads(archive_path.read_text(encoding='utf-8')) if archive_path.exists() else None
    rows = []
    for coverage in report['weeks']:
        week = coverage['week']
        snapshot_path = snapshot_dir / f'gw{week}.json'
        if not snapshot_path.exists() or archive is None:
            rows.append({'week': week, 'classification': 'not_evaluable', 'models':
                         {name: {'status': 'not_evaluable', 'reason': coverage['reason']}
                          for name in MODEL_NAMES}})
            continue
        snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
        try:
            evaluated = evaluate_week(snapshot, archive,
                                      lambda w, ids: _local_actuals(store, w, ids), predictor=predictor)
        except ValueError as exc:
            evaluated = {'week': week, 'classification': 'not_evaluable', 'models':
                         {name: {'status': 'not_evaluable', 'reason': str(exc)}
                          for name in MODEL_NAMES}}
        for name in MODEL_NAMES:
            evaluated['models'].setdefault(name, {'status': 'not_evaluable',
                                                    'reason': 'required_historical_inputs_unavailable'})
        rows.append(evaluated)
    by_model = {}
    for name in MODEL_NAMES:
        scored = [row['models'][name] for row in rows if row['models'][name]['status'] ==
                  'retrospective_reconstruction']
        by_model[name] = {'evaluated_weeks': len(scored),
                          'team_metrics': _metrics([r['error'] for r in scored]),
                          'player_metrics': _metrics([p['error'] for r in scored for p in r['players']]),
                          'recent_3_baseline': _metrics([r['actual_points'] - r['baselines']['recent_3_baseline']
                                                         for r in scored if r['baselines']['recent_3_baseline'] is not None]),
                          'season_to_date_baseline': _metrics([r['actual_points'] - r['baselines']['season_to_date_baseline']
                                                               for r in scored if r['baselines']['season_to_date_baseline'] is not None])}
    report['comparison_by_gameweek'] = rows
    report['cumulative_by_model'] = by_model
    report['verified_historical_count'] = 0
    report['retrospective_reconstruction_count'] = sum(
        item['status'] == 'retrospective_reconstruction' for row in rows for item in row['models'].values())
    return report


def save_report(report, directory=REPORT_DIR):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = directory / 'comparison.json', directory / 'comparison.csv'
    cumulative_path = directory / 'cumulative.csv'
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=('week', 'model', 'classification', 'status',
            'reason', 'predicted_points', 'actual_points', 'starting_xi_actual_points',
            'captain_contribution', 'team_mae', 'team_rmse', 'player_mae', 'player_rmse',
            'coverage', 'recent_3_baseline', 'season_to_date_baseline'))
        writer.writeheader()
        for row in report['comparison_by_gameweek']:
            for name, result in row['models'].items():
                team = _metrics([result['error']]) if 'error' in result else {}
                player = result.get('player_metrics') or {}
                writer.writerow({'week': row['week'], 'model': name, 'classification': row['classification'],
                    'status': result['status'], 'reason': result.get('reason'),
                    'predicted_points': result.get('predicted_points'), 'actual_points': result.get('actual_points'),
                    'starting_xi_actual_points': result.get('starting_xi_actual_points'),
                    'captain_contribution': result.get('captain_contribution'),
                    'team_mae': team.get('mae'), 'team_rmse': team.get('rmse'),
                    'player_mae': player.get('mae'), 'player_rmse': player.get('rmse'),
                    'coverage': result.get('coverage'),
                    'recent_3_baseline': (result.get('baselines') or {}).get('recent_3_baseline'),
                    'season_to_date_baseline': (result.get('baselines') or {}).get('season_to_date_baseline')})
    with cumulative_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=('model', 'evaluated_weeks', 'team_mae', 'team_rmse',
            'player_mae', 'player_rmse', 'recent_3_baseline_mae', 'recent_3_baseline_rmse',
            'season_to_date_baseline_mae', 'season_to_date_baseline_rmse'))
        writer.writeheader()
        for name, item in report['cumulative_by_model'].items():
            writer.writerow({'model': name, 'evaluated_weeks': item['evaluated_weeks'],
                'team_mae': item['team_metrics']['mae'], 'team_rmse': item['team_metrics']['rmse'],
                'player_mae': item['player_metrics']['mae'], 'player_rmse': item['player_metrics']['rmse'],
                'recent_3_baseline_mae': item['recent_3_baseline']['mae'],
                'recent_3_baseline_rmse': item['recent_3_baseline']['rmse'],
                'season_to_date_baseline_mae': item['season_to_date_baseline']['mae'],
                'season_to_date_baseline_rmse': item['season_to_date_baseline']['rmse']})
    return json_path, csv_path, cumulative_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Strict historical GW1-GW9 walk-forward audit')
    parser.add_argument('--store', type=Path, default=STORE)
    parser.add_argument('--snapshots', type=Path, default=SNAPSHOT_DIR)
    parser.add_argument('--output', type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    result = run(args.store, args.snapshots)
    paths = save_report(result, args.output)
    print(json.dumps({'verified': result['verified_historical_count'],
                      'retrospective': result['retrospective_reconstruction_count'],
                      'not_evaluable_weeks': [r['week'] for r in result['comparison_by_gameweek']
                                              if r['classification'] == 'not_evaluable'],
                      'reports': [str(p) for p in paths]}, indent=2))
