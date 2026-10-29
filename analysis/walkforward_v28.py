"""v2.8: risk-aware walk-forward with honest, separately scored calibration.

Uses the v2.7 candidate evaluator unchanged. Opponent identity remains retrospective.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from analysis.historical_backtest import STORE
from analysis.multiweek_backtest import MODELS, load_history
from analysis.walkforward_v27 import evaluate


def candidate_configs():
    configs = {f'{name}__plain': (config, 0.0) for name, config in MODELS.items()}
    configs.update({f'{name}__fixture': (config, 0.5) for name, config in MODELS.items()})
    return configs


def candidate_rank(rows, risk_penalty=0.35):
    """Reward realized points, penalize volatile week-to-week outcomes.

    A single observed week has no variance evidence, so use a fixed
    conservative prior dispersion instead of treating it as perfectly stable.
    """
    actuals = [r['actual'] for r in rows]
    if not actuals or any(v is None for v in actuals):
        raise ValueError('Training actuals missing')
    spread = pstdev(actuals) if len(actuals) > 1 else 15.0
    return mean(actuals) - risk_penalty * spread


def calibrate(raw, previous_rows, max_adjustment=12.0, prior_strength=4.0):
    """Shrink past forecast bias toward zero, cap corrections.

    No target-week outcomes are used. Calibration affects reporting only.
    """
    errors = [r['actual'] - r['predicted'] for r in previous_rows]
    if not errors:
        return round(raw, 2), 0.0
    bias = sum(errors) / (len(errors) + prior_strength)
    bias = max(-max_adjustment, min(max_adjustment, bias))
    return round(max(0, raw + bias), 2), round(bias, 3)


def walk_forward(records, weeks=(5, 6, 7, 8, 9), min_participation=.25,
                 risk_penalty=.35, optimizer=None, evaluator=None):
    weeks = tuple(weeks)
    if not weeks or list(weeks) != sorted(set(weeks)) or min(weeks) < 2:
        raise ValueError('Weeks must be ascending, distinct and >= 2')
    if not 0 <= min_participation <= 1 or risk_penalty < 0:
        raise ValueError('Invalid parameters')
    evaluator = evaluator or evaluate
    configs = candidate_configs()
    cache = {}
    for week in weeks:
        for name, (config, fixture_weight) in configs.items():
            print(f'GW{week}: {name}', flush=True)
            cache[(week, name)] = evaluator(records, week, config, fixture_weight,
                                            min_participation, optimizer)
    steps = []
    for idx, week in enumerate(weeks):
        prior = weeks[:idx]
        if not prior:
            steps.append({'week': week, 'selected_model': None, 'training_weeks': [],
                          'result': None, 'all_models': {n: {k: cache[(week, n)][k] for k in
                          ('predicted', 'actual', 'absolute_error')} for n in configs}})
            continue
        scores = {}
        for name in configs:
            rows = [cache[(w, name)] for w in prior]
            scores[name] = candidate_rank(rows, risk_penalty)
        selected = min(configs, key=lambda n: (-scores[n],
                       mean(cache[(w, n)]['absolute_error'] for w in prior), n))
        base = cache[(week, selected)]
        past = [cache[(w, selected)] for w in prior]
        raw = base['predicted']
        adjusted, bias = calibrate(raw, past)
        actual = base['actual']
        result = dict(base, raw_predicted=raw, calibrated_predicted=adjusted,
                      calibration_bias=bias,
                      raw_absolute_error=None if actual is None else round(abs(raw - actual), 2),
                      calibrated_absolute_error=None if actual is None else round(abs(adjusted - actual), 2))
        # Preserve raw predicted and absolute_error fields from v2.7 evaluator.
        steps.append({'week': week, 'selected_model': selected, 'training_weeks': list(prior),
                      'training_risk_adjusted_score': round(scores[selected], 3),
                      'training_mean_actual': round(mean(r['actual'] for r in past), 3),
                      'result': result,
                      'all_models': {n: {k: cache[(week, n)][k] for k in
                      ('predicted', 'actual', 'absolute_error')} for n in configs}})
    scored = [s['result'] for s in steps if s['result'] and s['result']['actual'] is not None]
    summary = {'scored_weeks': len(scored)}
    if scored:
        summary.update(mean_actual=round(mean(r['actual'] for r in scored), 3),
                       mean_raw_predicted=round(mean(r['raw_predicted'] for r in scored), 3),
                       mean_calibrated_predicted=round(mean(r['calibrated_predicted'] for r in scored), 3),
                       raw_mae=round(mean(r['raw_absolute_error'] for r in scored), 3),
                       calibrated_mae=round(mean(r['calibrated_absolute_error'] for r in scored), 3))
    return {'created_utc': datetime.now(timezone.utc).isoformat(),
            'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'selection_rule': 'Highest previous-week mean actual minus risk_penalty * population SD; tie-break lower prior raw MAE',
            'risk_penalty': risk_penalty,
            'calibration': 'Prior-only additive bias shrunk by four pseudo-observations and capped at ±12 points; reporting only',
            'candidates': list(configs), 'weeks': steps, 'summary': summary,
            'limitations': ['Historical opponent identities not verified at deadlines.',
                            'Historical player pool, injuries, suspensions and prices not point-in-time verified.',
                            'No autosubs, chips or transfer penalties.',
                            'Only a few training weeks; model selection is highly uncertain.',
                            'Calibration does not alter player selection, formation or captain.']}


def save_report(report, store=STORE):
    folder = Path(store)
    folder.mkdir(parents=True, exist_ok=True)
    jp, cp = folder / 'walkforward_backtest_v28.json', folder / 'walkforward_backtest_v28.csv'
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with cp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['week', 'model', 'selected', 'raw_predicted',
                 'calibrated_predicted', 'actual', 'raw_absolute_error', 'calibrated_absolute_error',
                 'calibration_bias', 'formation', 'captain'])
        writer.writeheader()
        for step in report['weeks']:
            for name, candidate in step['all_models'].items():
                chosen = step['selected_model'] == name
                r = step['result'] if chosen else {}
                writer.writerow({'week': step['week'], 'model': name, 'selected': chosen,
                     'raw_predicted': candidate['predicted'],
                     'calibrated_predicted': r.get('calibrated_predicted'),
                     'actual': candidate['actual'],
                     'raw_absolute_error': candidate['absolute_error'],
                     'calibrated_absolute_error': r.get('calibrated_absolute_error'),
                     'calibration_bias': r.get('calibration_bias'),
                     'formation': r.get('formation'), 'captain': r.get('captain')})
    return jp, cp


def main():
    parser = argparse.ArgumentParser(description='v2.8 risk-aware walk-forward')
    parser.add_argument('--weeks', nargs='+', type=int, default=[5, 6, 7, 8, 9])
    parser.add_argument('--min-participation', type=float, default=.25)
    parser.add_argument('--risk-penalty', type=float, default=.35)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.collect:
        from analysis.historical_backtest import collect
        collect(force=args.force)
    records = load_history()
    report = walk_forward(records, args.weeks, args.min_participation, args.risk_penalty)
    j, c = save_report(report)
    print('Summary:', report['summary'])
    print('JSON:', j, '\nCSV:', c)


if __name__ == '__main__':
    main()
