"""Retrospective player-point evaluation with no current roster inputs.

Historical TFF result rows supply outcomes and earlier-week points. They do not
contain historical fantasy positions, so the five position-prior forecasts are
reported as unavailable until point-in-time position evidence is supplied.
"""
import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from analysis.multiweek_backtest import MODELS

STORE = Path('historical_data')
OUTPUT = STORE / 'player_level_phase11'
BASELINES = ('recent_3_average', 'season_to_date_average')
MIN_HISTORY = {'short_form_3w': 3, 'baseline_5w': 5, 'conservative_5w': 5,
               'robust_5w': 5, 'stable_8w': 8}
FINISHED = {'FT', 'FINISHED', 'COMPLETED'}


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and
            math.isfinite(value))


def _fixture_teams(entry):
    """Fixture outcomes validate results; they are never forecast features."""
    matches = entry.get('matches') if isinstance(entry, dict) else None
    if not isinstance(matches, list) or not matches:
        return None
    teams = {}
    match_ids = set()
    used_clubs = set()
    for match in matches:
        mid, home, away = (match.get(k) for k in ('id', 'homeClubId', 'awayClubId'))
        if mid is None or home is None or away is None or str(home) == str(away) or mid in match_ids or \
           str(home) in used_clubs or str(away) in used_clubs:
            return None
        if str(match.get('status') or '').upper() not in FINISHED or \
           not _number(match.get('homeScore')) or not _number(match.get('awayScore')):
            return None
        match_ids.add(mid)
        used_clubs.update((str(home), str(away)))
        # For a player's row, the opponent + H/A must identify one match.
        teams[(str(away), 'H')] = str(home)
        teams[(str(home), 'A')] = str(away)
    if len(teams) != 2 * len(matches):
        return None
    return teams


def valid_row(row, week, entry):
    if not isinstance(row, dict) or row.get('gameweekOrder') != week or \
       row.get('gameweekId') != entry.get('gameweek_id') or not _number(row.get('points')):
        return False, 'missing_or_inconsistent_result'
    played, minutes = row.get('played'), row.get('minutesPlayed')
    if not isinstance(played, bool) or not _number(minutes) or minutes < 0 or \
       played != (minutes > 0):
        return False, 'appearance_minutes_inconsistent'
    if not played and row['points'] != 0:
        return False, 'nonappearance_nonzero_points'
    teams = _fixture_teams(entry)
    if teams is None or (str(row.get('opponentClubId')), row.get('homeAway')) not in teams:
        return False, 'incorrect_fixture_mapping'
    return True, None


def _metric(rows, seed=11, replicates=350):
    """Player-cluster bootstrap keeps repeated weeks for one player together."""
    if not rows:
        return {'n': 0, 'players': 0, 'mae': None, 'rmse': None, 'bias': None,
                'mae_ci_95': None, 'rmse_ci_95': None, 'bias_ci_95': None,
                'overpredictions': 0, 'underpredictions': 0, 'exact': 0}
    errors = [r['predicted'] - r['actual'] for r in rows]
    def point(values):
        return (mean(abs(v) for v in values), math.sqrt(mean(v*v for v in values)), mean(values))
    mae, rmse, bias = point(errors)
    groups = defaultdict(list)
    for row, error in zip(rows, errors):
        groups[str(row['player_id'])].append(error)
    ids = sorted(groups)
    rng = random.Random(seed)
    samples = [[], [], []]
    if len(ids) >= 2:
        for _ in range(replicates):
            drawn = [value for _ in ids for value in groups[rng.choice(ids)]]
            for bucket, value in zip(samples, point(drawn)):
                bucket.append(value)
    def interval(values):
        if not values:
            return None
        ordered = sorted(values)
        return [round(ordered[int(.025*(len(ordered)-1))], 3),
                round(ordered[int(.975*(len(ordered)-1))], 3)]
    return {'n': len(rows), 'players': len(ids), 'mae': round(mae, 3),
            'rmse': round(rmse, 3), 'bias': round(bias, 3),
            'mae_ci_95': interval(samples[0]), 'rmse_ci_95': interval(samples[1]),
            'bias_ci_95': interval(samples[2]),
            'overpredictions': sum(v > 0 for v in errors),
            'underpredictions': sum(v < 0 for v in errors),
            'exact': sum(v == 0 for v in errors)}


def _paired_difference(first, second, seed=29, replicates=500):
    """MAE difference for matched rows, bootstrapped by player identity."""
    if len(first) != len(second) or any((a['player_id'], a['week']) !=
                                       (b['player_id'], b['week']) for a, b in zip(first, second)):
        raise ValueError('Baselines must use identical player-week observations')
    if not first:
        return {'n': 0, 'mae_difference': None, 'ci_95': None}
    groups = defaultdict(list)
    for a, b in zip(first, second):
        groups[str(a['player_id'])].append(abs(a['predicted']-a['actual']) -
                                           abs(b['predicted']-b['actual']))
    ids = sorted(groups)
    delta = mean(v for values in groups.values() for v in values)
    values = []
    if len(ids) >= 2:
        rng = random.Random(seed)
        for _ in range(replicates):
            values.append(mean(v for _ in ids for v in groups[rng.choice(ids)]))
    values.sort()
    return {'n': len(first), 'mae_difference': round(delta, 3),
            'ci_95': [round(values[int(.025*(len(values)-1))], 3),
                      round(values[int(.975*(len(values)-1))], 3)] if values else None}


def _load_records(store):
    records = {}
    for path in sorted(Path(store).glob('player_*.json')):
        pid = path.stem.removeprefix('player_')
        if not pid.isdigit():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        records[pid] = data if isinstance(data, list) else []
    return records


def baseline_predictions(past, target_week):
    """Only point values from strictly earlier gameweeks enter either baseline."""
    if not past or any(not isinstance(row.get('gameweekOrder'), int) or
                       row['gameweekOrder'] >= target_week or not _number(row.get('points'))
                       for row in past):
        raise ValueError('Missing or future data in historical baseline input')
    points = [row['points'] for row in sorted(past, key=lambda row: row['gameweekOrder'])]
    return {'recent_3_average': mean(points[-3:]), 'season_to_date_average': mean(points)}


def audit(store=STORE):
    store = Path(store)
    records = _load_records(store)
    fixture_path = store / 'tff_fixtures_verified_v5.json'
    archive = json.loads(fixture_path.read_text(encoding='utf-8')) if fixture_path.exists() else {}
    weeks = []
    for week in range(2, 10):
        entry = (archive.get('weeks') or {}).get(str(week)) or {}
        counters = Counter()
        fixture_valid = _fixture_teams(entry) is not None
        for rows in records.values():
            target = [r for r in rows if isinstance(r, dict) and r.get('gameweekOrder') == week]
            if not target:
                counters['missing_target_rows'] += 1
                continue
            if len(target) != 1:
                counters['duplicate_target_rows'] += 1
                continue
            valid, reason = valid_row(target[0], week, entry)
            if not valid:
                counters[reason] += 1
                continue
            counters['valid_target_rows'] += 1
            counters['explicit_nonappearances' if not target[0]['played'] else 'appearances'] += 1
            if target[0]['played'] and target[0]['points'] == 0:
                counters['zero_point_appearances'] += 1
            past = [r for r in rows if isinstance(r, dict) and isinstance(r.get('gameweekOrder'), int)
                    and r['gameweekOrder'] < week]
            valid_past = []
            for row in past:
                prior_entry = (archive.get('weeks') or {}).get(str(row['gameweekOrder'])) or {}
                if valid_row(row, row['gameweekOrder'], prior_entry)[0]:
                    valid_past.append(row)
            if len(valid_past) == len(past) and len({r['gameweekOrder'] for r in past}) == len(past):
                for length in (1, 3, 5, 8):
                    counters[f'with_{length}_prior'] += len(past) >= length
        weeks.append({'week': week, 'fixture_complete': fixture_valid,
                      'fixture_count': len(entry.get('matches') or []),
                      **{key: counters[key] for key in ('valid_target_rows', 'appearances',
                          'explicit_nonappearances', 'zero_point_appearances', 'missing_target_rows',
                          'duplicate_target_rows', 'missing_or_inconsistent_result',
                          'appearance_minutes_inconsistent', 'incorrect_fixture_mapping',
                          'with_1_prior', 'with_3_prior', 'with_5_prior', 'with_8_prior')}})
    return {'history_files': len(records), 'weeks': weeks,
            'forecast_model_status': {name: {'status': 'not_evaluable',
                'reason': 'historical_position_unavailable_for_position_prior',
                'minimum_prior_weeks': MIN_HISTORY[name]} for name in MIN_HISTORY},
            'baseline_status': {name: 'retrospective_reconstruction' for name in BASELINES},
            'limitations': ['Player histories do not contain historical fantasy positions.',
                            'Current players.json and postdeadline GW9 output are excluded.',
                            'Fixture archive was collected after the evaluated gameweeks.',
                            'No player-level metric implies full-squad performance.']}


def evaluate(store=STORE):
    """Chronological GW2–GW9; target rows are read only for scoring and validation."""
    store = Path(store)
    records = _load_records(store)
    fixture_path = store / 'tff_fixtures_verified_v5.json'
    archive = json.loads(fixture_path.read_text(encoding='utf-8')) if fixture_path.exists() else {}
    coverage = audit(store)
    weekly = []
    all_observations = {label: {'unconditional': [], 'appearance': []} for label in BASELINES}
    for week in range(2, 10):
        entry = (archive.get('weeks') or {}).get(str(week)) or {}
        observations = {label: {'unconditional': [], 'appearance': []} for label in BASELINES}
        if _fixture_teams(entry) is not None:
            for pid, rows in sorted(records.items(), key=lambda item: int(item[0])):
                target = [r for r in rows if isinstance(r, dict) and r.get('gameweekOrder') == week]
                if len(target) != 1 or not valid_row(target[0], week, entry)[0]:
                    continue
                past = [r for r in rows if isinstance(r, dict) and isinstance(r.get('gameweekOrder'), int)
                        and r['gameweekOrder'] < week]
                if not past or len({r['gameweekOrder'] for r in past}) != len(past):
                    continue
                if any(not valid_row(r, r['gameweekOrder'],
                                     (archive.get('weeks') or {}).get(str(r['gameweekOrder'])) or {})[0]
                       for r in past):
                    continue
                actual = target[0]['points']
                predictions = baseline_predictions(past, week)
                for label, prediction in predictions.items():
                    item = {'week': week, 'player_id': pid, 'predicted': prediction,
                            'actual': actual, 'played': target[0]['played']}
                    observations[label]['unconditional'].append(item)
                    all_observations[label]['unconditional'].append(item)
                    if target[0]['played']:
                        observations[label]['appearance'].append(item)
                        all_observations[label]['appearance'].append(item)
        model_status = {name: {'status': 'not_evaluable', 'reason':
                        'historical_position_unavailable_for_position_prior',
                        'minimum_prior_weeks': MIN_HISTORY[name],
                        'potential_history_sample': coverage['weeks'][week-2][f'with_{MIN_HISTORY[name]}_prior']}
                        for name in MIN_HISTORY}
        def week_metrics(label, target):
            result = _metric(observations[label][target], seed=week)
            denominator = coverage['weeks'][week-2][
                'valid_target_rows' if target == 'unconditional' else 'appearances']
            result['sample_coverage'] = round(result['n']/denominator, 4) if denominator else None
            return result
        weekly.append({'week': week, 'classification': 'retrospective_reconstruction',
                       'coverage': coverage['weeks'][week-2], 'models': model_status,
                       'baselines': {label: {target: week_metrics(label, target)
                                             for target in ('unconditional', 'appearance')}
                                     for label in BASELINES},
                       'paired_mae_difference': {target: _paired_difference(
                           observations[BASELINES[0]][target], observations[BASELINES[1]][target], seed=week)
                           for target in ('unconditional', 'appearance')}})
    cumulative = {name: {'status': 'not_evaluable', 'reason':
                  'historical_position_unavailable_for_position_prior',
                  'unconditional': _metric([]), 'appearance': _metric([])} for name in MIN_HISTORY}
    for label in BASELINES:
        def cumulative_metrics(target):
            result = _metric(all_observations[label][target])
            denominator = sum(w['valid_target_rows' if target == 'unconditional' else 'appearances']
                              for w in coverage['weeks'])
            result['sample_coverage'] = round(result['n']/denominator, 4) if denominator else None
            return result
        cumulative[label] = {'status': 'retrospective_reconstruction',
                             **{target: cumulative_metrics(target)
                                for target in ('unconditional', 'appearance')}}
    paired = {target: _paired_difference(all_observations[BASELINES[0]][target],
                                        all_observations[BASELINES[1]][target])
              for target in ('unconditional', 'appearance')}
    ranking = sorted(BASELINES, key=lambda name: (
        cumulative[name]['unconditional']['mae'], cumulative[name]['unconditional']['rmse']))
    rmse_ranking = sorted(BASELINES, key=lambda name: (
        cumulative[name]['unconditional']['rmse'], cumulative[name]['unconditional']['mae']))
    return {'classification': 'retrospective_player_level_only', 'target_weeks': list(range(2, 10)),
            'data_audit': coverage, 'by_gameweek': weekly, 'cumulative': cumulative,
            'baseline_definition': {'recent_3_average': 'Mean of up to three available, validated earlier gameweeks; at least one required.',
                                    'season_to_date_average': 'Mean of all available, validated earlier gameweeks; at least one required.'},
            'paired_baseline_mae_difference': paired,
            'ranking': [{'rank': i+1, 'model': name,
                         'mae': cumulative[name]['unconditional']['mae'],
                         'rmse': cumulative[name]['unconditional']['rmse'],
                         'n': cumulative[name]['unconditional']['n']}
                        for i, name in enumerate(ranking)],
            'ranking_by_rmse': [{'rank': i+1, 'model': name,
                                 'mae': cumulative[name]['unconditional']['mae'],
                                 'rmse': cumulative[name]['unconditional']['rmse'],
                                 'n': cumulative[name]['unconditional']['n']}
                                for i, name in enumerate(rmse_ranking)],
            'ranking_scope': 'Only evaluable simple baselines; five production form models lack historical position inputs.',
            'bias_sign': 'Positive bias means predicted points exceeded actual points.',
            'uncertainty_method': '95% percentile bootstrap by player ID, 350 replicates for metrics and 500 for paired MAE differences.',
            'limitations': coverage['limitations'] + [
                'Player-cluster uncertainty intervals do not fully account for shared match or gameweek shocks.']}


def save_report(report, output=OUTPUT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    detailed = output / 'player_level_report.json'
    weekly = output / 'player_level_comparison.csv'
    cumulative = output / 'player_level_cumulative.csv'
    detailed.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    columns = ('gameweek', 'model', 'target', 'status', 'reason', 'n', 'players', 'sample_coverage', 'mae', 'rmse',
               'bias', 'mae_ci_95', 'rmse_ci_95', 'bias_ci_95', 'overpredictions',
               'underpredictions', 'exact', 'valid_target_rows', 'explicit_nonappearances')
    with weekly.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for week in report['by_gameweek']:
            for name, model in week['models'].items():
                for target in ('unconditional', 'appearance'):
                    writer.writerow({'gameweek': week['week'], 'model': name, 'target': target,
                                     'status': model['status'], 'reason': model['reason'],
                                     'valid_target_rows': week['coverage']['valid_target_rows'],
                                     'explicit_nonappearances': week['coverage']['explicit_nonappearances']})
            for name, targets in week['baselines'].items():
                for target, metrics in targets.items():
                    writer.writerow({'gameweek': week['week'], 'model': name, 'target': target,
                        'status': 'retrospective_reconstruction',
                        **{key: json.dumps(value) if isinstance(value, list) else value
                           for key, value in metrics.items()},
                        'valid_target_rows': week['coverage']['valid_target_rows'],
                        'explicit_nonappearances': week['coverage']['explicit_nonappearances']})
    cumulative_columns = tuple(c for c in columns if c not in ('gameweek', 'valid_target_rows',
                                                               'explicit_nonappearances'))
    with cumulative.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=cumulative_columns)
        writer.writeheader()
        for name, item in report['cumulative'].items():
            for target in ('unconditional', 'appearance'):
                writer.writerow({'model': name, 'target': target, 'status': item['status'],
                    'reason': item.get('reason'),
                    **({key: json.dumps(value) if isinstance(value, list) else value
                        for key, value in item[target].items()}
                       if item['status'] == 'retrospective_reconstruction' else {})})
    return weekly, cumulative, detailed


def main():
    parser = argparse.ArgumentParser(description='Player-level GW2-GW9 retrospective evaluation')
    parser.add_argument('--store', type=Path, default=STORE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = evaluate(args.store)
    paths = save_report(result, args.output)
    print(json.dumps({'ranking': result['ranking'], 'paired_mae_difference':
                      result['paired_baseline_mae_difference']['unconditional'],
                      'files': [str(path) for path in paths]}, indent=2))


if __name__ == '__main__':
    main()
