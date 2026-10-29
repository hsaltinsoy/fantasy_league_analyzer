"""v2.9: player-level historical calibration and risk-aware captaincy.

All player features use rounds strictly before target. The fixture opponent id
still comes from the post-match archive: NOT point-in-time verified.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from analysis.historical_backtest import STORE, number
from analysis.multiweek_backtest import MODELS, load_history
from analysis.walkforward_v27 import build_v27_pool
from analysis.walkforward_v28 import candidate_configs, candidate_rank


def player_adjustment(rows, week, window=6, prior_strength=6, max_adjustment=1.5):
    """Shrink past realized points around their prior mean (not in-sample fitted errors).

    This is an empirical form correction, not a fitted forecast-residual model.
    """
    past = sorted((r for r in rows if int(r['gameweekOrder']) < week),
                  key=lambda r: int(r['gameweekOrder']))[-window:]
    values = [number(r.get('points')) for r in past if number(r.get('points')) is not None]
    if len(values) < 2:
        return 0.0
    recent = values[-min(3, len(values)):]
    shift = (mean(recent) - mean(values)) * len(values) / (len(values) + prior_strength)
    return max(-max_adjustment, min(max_adjustment, shift))


def captain_risk(rows, week, window=6):
    past = sorted((r for r in rows if int(r['gameweekOrder']) < week),
                  key=lambda r: int(r['gameweekOrder']))[-window:]
    pts = [number(r.get('points')) for r in past if number(r.get('points')) is not None]
    if len(pts) < 3:
        return 0.0
    return min(10.0, pstdev(pts))


def evaluate_v29(records, week, config, fixture_weight, min_participation=.25,
                 calibration_strength=1.0, captain_risk_penalty=.2, optimizer=None):
    if optimizer is None:
        from analysis.optimizer import optimize
        optimizer = optimize
    pool, actual, coverage = build_v27_pool(records, week, config, fixture_weight, min_participation)
    histories = {str(p['id']): rows for p, rows in records}
    for p in pool:
        rows = histories[str(p['id'])]
        adjustment = player_adjustment(rows, week) * calibration_strength
        p['original_xpts'] = p['xpts']
        p['player_adjustment'] = round(adjustment, 3)
        p['xpts'] = round(max(.1, p['xpts'] + adjustment), 3)
        p['captain_risk'] = round(captain_risk(rows, week), 3)
        # Optimize captain bonus separately while keeping XI points unchanged.
        p['captain_bonus_xpts'] = max(.1, p['xpts'] - captain_risk_penalty * p['captain_risk'])
    result = optimizer(pool)
    if 'error' in result:
        raise ValueError(result['error'])
    xi = result['starting_xi']
    captain_id = str(result['captain']['id'])
    missing = [p['id'] for p in xi if actual.get(str(p['id'])) is None]
    score = None if missing else round(sum(actual[str(p['id'])] * (2 if str(p['id']) == captain_id else 1) for p in xi), 2)
    forecast = round(sum(p['xpts'] + (p['captain_bonus_xpts'] if str(p['id']) == captain_id else 0) for p in xi), 2)
    return {'week': week, 'formation': result['formation'], 'captain': result['captain']['name'],
            'predicted': forecast, 'actual': score,
            'absolute_error': None if score is None else round(abs(forecast - score), 2),
            'eligible_players': len(pool), 'budget': result['squad_cost'], 'coverage': coverage,
            'starting_xi': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                             'xpts': p['xpts'], 'original_xpts': p['original_xpts'],
                             'player_adjustment': p['player_adjustment'],
                             'captain_risk': p['captain_risk'], 'actual_points': actual.get(str(p['id'])),
                             'captain': str(p['id']) == captain_id} for p in xi],
            'bench': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                       'xpts': p['xpts'], 'actual_points': actual.get(str(p['id']))}
                      for p in result['squad'] if p['id'] not in {x['id'] for x in xi}],
            'missing_actual_ids': missing}


def walk_forward(records, weeks=(5, 6, 7, 8, 9), min_participation=.25,
                 risk_penalty=.35, optimizer=None, evaluator=None):
    weeks = tuple(weeks)
    if not weeks or list(weeks) != sorted(set(weeks)) or min(weeks) < 2:
        raise ValueError('Weeks must be distinct ascending integers >= 2')
    if not 0 <= min_participation <= 1 or risk_penalty < 0:
        raise ValueError('Invalid thresholds')
    evaluator = evaluator or evaluate_v29
    # Pre-registered variants: v2.8-like control, player calibration only,
    # captain risk only, and both. No target-week outcome in selection.
    variants = {'control': (0., 0.), 'player': (1., 0.),
                'captain': (0., .2), 'combined': (1., .2)}
    configs = candidate_configs()
    cache = {}
    for week in weeks:
        for name, (config, fixture_weight) in configs.items():
            for variant, (calibration, captain_penalty) in variants.items():
                key = f'{name}__{variant}'
                print(f'GW{week}: {key}', flush=True)
                cache[(week, key)] = evaluator(records, week, config, fixture_weight,
                    min_participation, calibration, captain_penalty, optimizer)
    names = [f'{name}__{variant}' for name in configs for variant in variants]
    steps = []
    for i, week in enumerate(weeks):
        prior = weeks[:i]
        selected = None
        if prior:
            def rank(name):
                rows = [cache[(w, name)] for w in prior]
                return (-candidate_rank(rows, risk_penalty),
                        mean(r['absolute_error'] for r in rows), name)
            selected = min(names, key=rank)
        result = cache[(week, selected)] if selected else None
        steps.append({'week': week, 'training_weeks': list(prior), 'selected_model': selected,
                      'result': result,
                      'all_models': {n: {k: cache[(week, n)][k] for k in ('predicted', 'actual', 'absolute_error')}
                                     for n in names}})
    scored = [s['result'] for s in steps if s['result'] and s['result']['actual'] is not None]
    return {'created_utc': datetime.now(timezone.utc).isoformat(),
            'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'selection_rule': 'Prior weeks only: mean actual minus risk penalty * population SD; raw MAE tie-break',
            'variants': {k: {'player_calibration_strength': v[0], 'captain_risk_penalty': v[1]}
                         for k, v in variants.items()},
            'weeks': steps,
            'summary': {'scored_weeks': len(scored),
                        'mean_actual': round(mean(r['actual'] for r in scored), 3) if scored else None,
                        'mae': round(mean(r['absolute_error'] for r in scored), 3) if scored else None},
            'limitations': ['Fixture opponent identities from post-match archive, not verified at deadline.',
                            'Player pool, historical prices, injuries and suspensions not point-in-time verified.',
                            'Player adjustment is recent-form shrinkage, not fitted forecast-residual calibration.',
                            'No auto-subs, chips, or transfer penalties.',
                            '32 candidates and few weeks create substantial model-selection overfitting risk.']}


def save_report(report, store=STORE):
    folder = Path(store)
    folder.mkdir(parents=True, exist_ok=True)
    jp, cp = folder / 'walkforward_backtest_v29.json', folder / 'walkforward_backtest_v29.csv'
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with cp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['week', 'model', 'selected', 'predicted', 'actual', 'absolute_error', 'formation', 'captain'])
        writer.writeheader()
        for step in report['weeks']:
            for name, row in step['all_models'].items():
                chosen = step['selected_model'] == name
                result = step['result'] if chosen else {}
                writer.writerow({'week': step['week'], 'model': name, 'selected': chosen, **row,
                                 'formation': result.get('formation'), 'captain': result.get('captain')})
    return jp, cp


def main():
    parser = argparse.ArgumentParser(description='v2.9 player and captain risk walk-forward')
    parser.add_argument('--weeks', nargs='+', type=int, default=[5, 6, 7, 8, 9])
    parser.add_argument('--min-participation', type=float, default=.25)
    parser.add_argument('--risk-penalty', type=float, default=.35)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.collect:
        from analysis.historical_backtest import collect
        collect(force=args.force)
    report = walk_forward(load_history(), args.weeks, args.min_participation, args.risk_penalty)
    j, c = save_report(report)
    print('Summary:', report['summary'])
    print('JSON:', j, '\nCSV:', c)


if __name__ == '__main__':
    main()
