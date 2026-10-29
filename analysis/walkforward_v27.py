"""v2.7: causal-history fixture proxy and calibrated walk-forward model selection.

Historical opponent identity is read from target-round history (post-match archive),
so this remains retrospective, NOT a verified deadline snapshot.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from analysis.historical_backtest import STORE, number
from analysis.multiweek_backtest import MODELS, load_history
from analysis.walkforward_backtest import week_pool


def fixture_multipliers(records, week, min_samples=8, prior_samples=24):
    """Opponent fantasy points conceded, using games STRICTLY before week."""
    by_opponent = defaultdict(list)
    by_position = defaultdict(list)
    for player, rows in records:
        position = player['position']
        for row in rows:
            if int(row['gameweekOrder']) >= week or number(row.get('minutesPlayed'), 0) <= 0:
                continue
            pts = number(row.get('points'))
            opponent = row.get('opponentClubId')
            if pts is None or opponent in (None, ''):
                continue
            by_opponent[(str(opponent), position)].append(pts)
            by_position[position].append(pts)
    result = {}
    for (opponent, position), points in by_opponent.items():
        baseline = mean(by_position[position]) if by_position[position] else 3.0
        if len(points) < min_samples or baseline <= 0:
            continue
        # Shrink heavily to 1 and clip to avoid noisy fixture effects.
        ratio = (sum(points) + prior_samples * baseline) / ((len(points) + prior_samples) * baseline)
        result[(opponent, position)] = max(.85, min(1.15, ratio))
    return result


def build_v27_pool(records, week, config, fixture_weight=.5, min_participation=.25):
    pool, actual, coverage = week_pool(records, week, config, min_participation)
    target_by_id = {}
    for player, rows in records:
        target = next((r for r in rows if int(r['gameweekOrder']) == week), None)
        if target:
            target_by_id[str(player['id'])] = target
    fixture = fixture_multipliers(records, week)
    used, missing = 0, 0
    for p in pool:
        row = target_by_id.get(str(p['id']), {})
        opponent = row.get('opponentClubId')
        key = (str(opponent), p['position'])
        factor = fixture.get(key)
        if factor is None:
            missing += 1
            factor = 1.0
        else:
            used += 1
        p['base_xpts'] = p['xpts']
        p['fixture_factor'] = round(1 + fixture_weight * (factor - 1), 4)
        p['opponent_club_id'] = opponent
        p['xpts'] = round(max(.1, p['xpts'] * p['fixture_factor']), 3)
    coverage['fixture_proxy_applied'] = used
    coverage['fixture_proxy_unavailable'] = missing
    coverage['fixture_proxy_note'] = 'Target-week opponent is taken from post-match archive, not verified pre-deadline'
    return pool, actual, coverage


def evaluate(records, week, config, fixture_weight=.5, min_participation=.25, optimizer=None):
    if optimizer is None:
        from analysis.optimizer import optimize
        optimizer = optimize
    pool, actual, coverage = build_v27_pool(records, week, config, fixture_weight, min_participation)
    if len(pool) < 15:
        raise ValueError(f'Week {week}: insufficient players')
    result = optimizer(pool)
    if 'error' in result:
        raise ValueError(result['error'])
    xi = result['starting_xi']
    captain_id = str(result['captain']['id'])
    missing = [p['id'] for p in xi if actual.get(str(p['id'])) is None]
    score = None if missing else round(sum(actual[str(p['id'])] * (2 if str(p['id']) == captain_id else 1) for p in xi), 2)
    return {'week': week, 'formation': result['formation'], 'captain': result['captain']['name'],
            'predicted': result['expected_points'], 'actual': score,
            'absolute_error': None if score is None else round(abs(result['expected_points'] - score), 2),
            'budget': result['squad_cost'], 'eligible_players': len(pool), 'coverage': coverage,
            'missing_actual_ids': missing,
            'starting_xi': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                             'xpts': p['xpts'], 'actual_points': actual.get(str(p['id'])),
                             'captain': str(p['id']) == captain_id,
                             'participation_proxy': p['participation_proxy'],
                             'fixture_factor': p['fixture_factor']} for p in xi],
            'bench': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                       'xpts': p['xpts'], 'actual_points': actual.get(str(p['id']))}
                      for p in result['squad'] if p['id'] not in {x['id'] for x in xi}],
            'formation_comparison': result['formation_comparison']}


def walk_forward(records, weeks=(5,6,7,8,9), min_participation=.25, optimizer=None):
    weeks = tuple(weeks)
    if not weeks or sorted(set(weeks)) != list(weeks) or min(weeks) < 2:
        raise ValueError('Weeks must be ascending and distinct, >= 2')
    if not 0 <= min_participation <= 1:
        raise ValueError('Invalid participation threshold')
    # Predefined variants: compare unadjusted against conservative fixture adjustment.
    candidates = {f'{name}__plain': (config, 0.) for name, config in MODELS.items()}
    candidates.update({f'{name}__fixture': (config, .5) for name, config in MODELS.items()})
    cache = {}
    for week in weeks:
        for name, (config, weight) in candidates.items():
            print(f'GW{week}: {name}', flush=True)
            cache[(week, name)] = evaluate(records, week, config, weight, min_participation, optimizer)
    steps = []
    for index, week in enumerate(weeks):
        prior = weeks[:index]
        if prior:
            # Score selection prioritizes realized team points, then calibration error.
            # Prior weeks only. No current-week outcome enters selection.
            def rank(name):
                rows = [cache[(w, name)] for w in prior]
                if any(r['actual'] is None for r in rows):
                    raise ValueError('Missing prior-week actual points')
                return (-mean(r['actual'] for r in rows), mean(r['absolute_error'] for r in rows), name)
            selected = min(candidates, key=rank)
            result = cache[(week, selected)]
            prior_actual = round(-rank(selected)[0], 3)
            prior_mae = round(rank(selected)[1], 3)
            # Calibration is learned on prior weeks only; this affects reported
            # point forecasts, NOT lineup/captain optimization.
            prior_bias = mean(cache[(w, selected)]['actual'] - cache[(w, selected)]['predicted'] for w in prior)
            result = dict(result)
            result['raw_predicted'] = result['predicted']
            result['predicted'] = round(max(0., result['predicted'] + prior_bias), 2)
            result['calibration_bias'] = round(prior_bias, 2)
            result['absolute_error'] = None if result['actual'] is None else round(abs(result['predicted'] - result['actual']), 2)
        else:
            selected, result, prior_actual, prior_mae = None, None, None, None
        steps.append({'week': week, 'selected_model': selected, 'training_weeks': list(prior),
                      'training_mean_actual': prior_actual, 'training_mae': prior_mae,
                      'result': result,
                      'all_models': {name: {k: cache[(week, name)][k] for k in ('predicted', 'actual', 'absolute_error')}
                                     for name in candidates}})
    scored = [s['result'] for s in steps if s['result'] is not None and s['result']['actual'] is not None]
    return {'created_utc': datetime.now(timezone.utc).isoformat(),
            'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'selection_rule': 'Highest mean realized team points on earlier weeks, then lower raw MAE; no current-week leakage into selection',
            'calibration': 'Expanding-window additive bias from selected candidate on prior weeks; reporting only',
            'candidates': {name: {'model': name.split('__')[0], 'fixture_weight': weight, **config}
                           for name, (config, weight) in candidates.items()},
            'min_participation_proxy': min_participation, 'weeks': steps,
            'summary': {'scored_weeks': len(scored),
                        'mean_actual': round(mean(r['actual'] for r in scored), 3) if scored else None,
                        'mean_predicted': round(mean(r['predicted'] for r in scored), 3) if scored else None,
                        'mae': round(mean(r['absolute_error'] for r in scored), 3) if scored else None},
            'limitations': [
                'Target-week opponent identifiers come from retrospective history, not verified deadline snapshots.',
                'Opponent strength proxy uses fantasy points conceded by position in prior rounds, not verified pre-match odds or xG.',
                'Player list and team mapping are current snapshot; historical pool unverified.',
                'Historical injury/suspension and historical deadline prices are unverified.',
                'Minutes participation filter is a proxy, not confirmed availability; base model already discounts past minutes.',
                'Calibration changes displayed forecast only, not player selection or captain.',
                'No auto-subs, chips or transfer penalties; early weeks are a small sample.',
            ]}


def save_report(report, store=STORE):
    folder = Path(store)
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / 'walkforward_backtest_v27.json'
    csv_path = folder / 'walkforward_backtest_v27.csv'
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with csv_path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=['week', 'model', 'selected', 'predicted', 'actual', 'absolute_error', 'calibration_bias', 'formation', 'captain', 'eligible_players'])
        writer.writeheader()
        for step in report['weeks']:
            for name, data in step['all_models'].items():
                chosen = name == step['selected_model']
                result = step['result'] if chosen else {}
                writer.writerow({'week': step['week'], 'model': name, 'selected': chosen, **data,
                                 **({'predicted': result['predicted'], 'absolute_error': result['absolute_error']} if chosen else {}),
                                 'calibration_bias': result.get('calibration_bias'), 'formation': result.get('formation'),
                                 'captain': result.get('captain'), 'eligible_players': result.get('eligible_players')})
    return json_path, csv_path


def main():
    parser = argparse.ArgumentParser(description='v2.7 retrospective fixture-adjusted walk-forward')
    parser.add_argument('--weeks', nargs='+', type=int, default=[5,6,7,8,9])
    parser.add_argument('--min-participation', type=float, default=.25)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.collect:
        from analysis.historical_backtest import collect
        collect(force=args.force)
    records = load_history()
    print(f'{len(records)} player histories loaded')
    report = walk_forward(records, args.weeks, args.min_participation)
    j, c = save_report(report)
    for step in report['weeks']:
        r = step['result']
        print(f"GW{step['week']}: {step['selected_model']} | {('predicted '+str(r['predicted'])+' actual '+str(r['actual'])) if r else 'warm-up'}")
    print('Summary:', report['summary'])
    print('JSON:', j, '\nCSV:', c)


if __name__ == '__main__':
    main()
