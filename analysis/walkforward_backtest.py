"""v2.6 expanding-window walk-forward evaluation, using only prior-week features.

Usage: python -m analysis.walkforward_backtest --weeks 5 6 7 8 9
The optimizer is unchanged; this adds time-ordered model selection and a
past-minutes-only participation proxy. Not a verified point-in-time backtest.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from analysis.multiweek_backtest import MODELS, load_history, build_week
from analysis.historical_backtest import STORE, number


def participation(past, lookback=4):
    """Historical proxy only. Does not assert injury/suspension status."""
    recent = past[-lookback:]
    mins = [max(0, number(r.get('minutesPlayed'), 0)) for r in recent]
    if not mins:
        return {'probability': 0.0, 'avg_minutes': 0.0, 'starts_rate': 0.0}
    played = sum(m > 0 for m in mins) / len(mins)
    avg = mean(mins)
    starts = sum(bool(r.get('started')) for r in recent) / len(recent)
    # Bounded, conservative proxy based ONLY on preceding weeks.
    probability = min(1., max(0.05, .65 * played + .35 * min(1., avg / 75)))
    return {'probability': round(probability, 3), 'avg_minutes': round(avg, 1), 'starts_rate': round(starts, 3)}


def week_pool(records, week, config, min_probability=0.25):
    pool, actual, coverage = build_week(records, week, config)
    histories = {str(p['id']): rows for p, rows in records}
    filtered = []
    excluded = []
    for player in pool:
        past = [r for r in histories[str(player['id'])] if int(r['gameweekOrder']) < week]
        proxy = participation(past)
        if proxy['probability'] < min_probability:
            excluded.append(player['id'])
            continue
        p = dict(player)
        # Original project() already scales by recent minutes; do NOT multiply
        # xpts by the same factor again. Use proxy for eligibility only.
        p['participation_proxy'] = proxy['probability']
        p['recent_avg_minutes'] = proxy['avg_minutes']
        filtered.append(p)
    coverage['excluded_low_participation_proxy'] = len(excluded)
    coverage['proxy_threshold'] = min_probability
    coverage['excluded_player_ids'] = excluded
    return filtered, actual, coverage


def evaluate(records, week, config, min_probability=.25, optimizer=None):
    if optimizer is None:
        from analysis.optimizer import optimize
        optimizer = optimize
    pool, actual, coverage = week_pool(records, week, config, min_probability)
    if len(pool) < 15:
        raise ValueError(f'Week {week}: only {len(pool)} eligible players after proxy filter')
    result = optimizer(pool)
    if 'error' in result:
        raise ValueError(f'Week {week}: {result["error"]}')
    xi = result['starting_xi']
    captain = result['captain']
    missing = [p['id'] for p in xi if actual.get(str(p['id'])) is None]
    actual_score = None if missing else round(sum(actual[str(p['id'])] * (2 if p['id'] == captain['id'] else 1) for p in xi), 2)
    return {
        'week': week, 'formation': result['formation'], 'captain': captain['name'],
        'predicted': result['expected_points'], 'actual': actual_score,
        'absolute_error': None if actual_score is None else round(abs(result['expected_points'] - actual_score), 2),
        'budget': result['squad_cost'], 'eligible_players': len(pool), 'coverage': coverage,
        'missing_actual_ids': missing,
        'starting_xi': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                         'xpts': p['xpts'], 'actual_points': actual.get(str(p['id'])),
                         'captain': p['id'] == captain['id'],
                         'participation_proxy': p['participation_proxy']} for p in xi],
        'bench': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                   'xpts': p['xpts'], 'actual_points': actual.get(str(p['id']))}
                  for p in result['squad'] if p['id'] not in {x['id'] for x in xi}],
        'formation_comparison': result['formation_comparison'],
    }


def walk_forward(records, weeks=(5,6,7,8,9), models=None, min_probability=.25, optimizer=None):
    models = models or MODELS
    weeks = tuple(weeks)
    if sorted(set(weeks)) != list(weeks) or min(weeks) < 2:
        raise ValueError('Weeks must be distinct ascending integers >=2')
    if not 0 <= min_probability <= 1:
        raise ValueError('min_probability must be between 0 and 1')
    # First week has no training window. Evaluate each model, but do not select
    # a winner using that week's actual outcome.
    cache = {}
    for week in weeks:
        for name, config in models.items():
            print(f'{week}. hafta: {name}', flush=True)
            cache[(week, name)] = evaluate(records, week, config, min_probability, optimizer)
    steps = []
    for idx, week in enumerate(weeks):
        previous = weeks[:idx]
        if previous:
            def ranking(name):
                results = [cache[(w, name)] for w in previous]
                if any(r['actual'] is None for r in results):
                    raise ValueError('Missing actual score in earlier training week')
                return (mean(r['absolute_error'] for r in results), name)
            selected = min(models, key=ranking)
            train_mae = round(ranking(selected)[0], 3)
            chosen = cache[(week, selected)]
        else:
            selected, train_mae, chosen = None, None, None
        steps.append({'week': week, 'selected_model': selected, 'training_weeks': list(previous),
                      'training_mae': train_mae, 'result': chosen,
                      'all_models': {name: {'predicted': cache[(week,name)]['predicted'],
                                            'actual': cache[(week,name)]['actual'],
                                            'absolute_error': cache[(week,name)]['absolute_error']} for name in models}})
    valid = [s['result'] for s in steps if s['result'] is not None and s['result']['actual'] is not None]
    return {'created_utc': datetime.now(timezone.utc).isoformat(),
            'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'selection_rule': 'Expanding-window lowest team-score MAE using only prior evaluated weeks',
            'model_configs': models, 'min_participation_proxy': min_probability,
            'weeks': steps,
            'summary': {'scored_weeks': len(valid),
                        'mean_actual': round(mean(r['actual'] for r in valid), 3) if valid else None,
                        'mean_predicted': round(mean(r['predicted'] for r in valid), 3) if valid else None,
                        'mae': round(mean(r['absolute_error'] for r in valid), 3) if valid else None},
            'limitations': [
                'First evaluated week is a warm-up; no model selected without earlier training results.',
                'Player list and team mapping are from current snapshot; historical pool is unverified.',
                'Participation proxy is based on past minutes only; not confirmed historic injuries or suspensions.',
                'Past prices are last recorded price before the target round, not verified deadline prices.',
                'No verified historical fixture-strength data or historic xgEdge snapshots.',
                'No automatic substitutions, chips or transfer penalties.',
                'Models were specified in advance; interpretation still vulnerable to retrospective design bias.',
            ]}


def save_report(report, store=STORE):
    path = Path(store)
    path.mkdir(parents=True, exist_ok=True)
    j = path / 'walkforward_backtest_v26.json'
    c = path / 'walkforward_backtest_v26.csv'
    j.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with c.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['week', 'model', 'dataset', 'training_mae', 'predicted', 'actual', 'absolute_error', 'formation', 'captain', 'eligible_players'])
        writer.writeheader()
        for step in report['weeks']:
            for name, result in step['all_models'].items():
                chosen = step['selected_model'] == name
                detail = step['result'] if chosen else {}
                writer.writerow({'week': step['week'], 'model': name, 'dataset': 'selected' if chosen else 'candidate',
                                 'training_mae': step['training_mae'] if chosen else '',
                                 **result, 'formation': detail.get('formation', ''), 'captain': detail.get('captain', ''),
                                 'eligible_players': detail.get('eligible_players', '')})
    return j, c


def main():
    parser = argparse.ArgumentParser(description='v2.6 historical expanding-window backtest')
    parser.add_argument('--weeks', type=int, nargs='+', default=[5,6,7,8,9])
    parser.add_argument('--min-participation', type=float, default=.25)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.collect:
        from analysis.historical_backtest import collect
        collect(force=args.force)
    records = load_history()
    print(f'{len(records)} player histories loaded')
    report = walk_forward(records, args.weeks, min_probability=args.min_participation)
    j, c = save_report(report)
    for step in report['weeks']:
        r = step['result']
        if r:
            print(f"GW{step['week']}: {step['selected_model']} | predicted {r['predicted']} | actual {r['actual']} | error {r['absolute_error']}")
        else:
            print(f"GW{step['week']}: warm-up only (no prior training)")
    print('Summary:', report['summary'])
    print('JSON:', j, '\nCSV:', c)


if __name__ == '__main__':
    main()
