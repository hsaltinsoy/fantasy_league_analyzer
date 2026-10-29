"""Walk-forward retrospective model comparison.

Usage: python -m analysis.multiweek_backtest --collect
       python -m analysis.multiweek_backtest --train-rounds 5 6 7 8 --test-round 9

Selects a model using only training rounds and reports the held-out test round.
All model inputs for GW N are derived from player history with gameweekOrder < N.
"""
import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from analysis.historical_backtest import STORE, collect, number

PRIORS = {'GK': 3.1, 'DEF': 3.2, 'MID': 3.5, 'FWD': 3.6}
MODELS = {
    'baseline_5w': {'window': 5, 'shrinkage': 4, 'recent_mix': .55, 'recency': True},
    'conservative_5w': {'window': 5, 'shrinkage': 10, 'recent_mix': .40, 'recency': True},
    'short_form_3w': {'window': 3, 'shrinkage': 6, 'recent_mix': .60, 'recency': True},
    'stable_8w': {'window': 8, 'shrinkage': 8, 'recent_mix': .30, 'recency': False},
    'robust_5w': {'window': 5, 'shrinkage': 9, 'recent_mix': .38, 'recency': True, 'robust': True},
}


def load_history(store=STORE):
    players_path = Path(store) / 'players.json'
    if not players_path.exists():
        raise FileNotFoundError(f'{players_path} bulunamadı; önce --collect çalıştırın.')
    players = json.loads(players_path.read_text(encoding='utf-8'))
    records = []
    for p in players:
        path = Path(store) / f"player_{p['id']}.json"
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(rows, list):
            records.append((p, sorted((r for r in rows if isinstance(r, dict) and str(r.get('gameweekOrder', '')).isdigit()), key=lambda r: int(r['gameweekOrder']))))
    return records


def project(p, past, config):
    recent = past[-config['window']:]
    points = [number(r.get('points'), 0) for r in recent]
    minutes = [number(r.get('minutesPlayed'), 0) for r in recent]
    weights = list(range(1, len(points)+1)) if config['recency'] else [1] * len(points)
    if config.get('robust') and len(points) >= 3:
        # Damp one-off hauls without removing repeat high scorers.
        ordered = sorted(points)
        ceiling = ordered[-2] + max(2.0, .5 * (ordered[-2] - ordered[0]))
        points = [min(x, ceiling) for x in points]
    form = sum(v*w for v, w in zip(points, weights)) / sum(weights)
    season = mean(number(r.get('points'), 0) for r in past)
    prior = PRIORS.get(p['position'], 3.0)
    shrink = len(past) / (len(past) + config['shrinkage'])
    availability = min(1, max(.1, mean(minutes) / 85))
    return round(max(.1, (config['recent_mix'] * (shrink*form + (1-shrink)*prior) + (1-config['recent_mix'])*season) * availability), 3)


def build_week(records, week, config):
    pool, actual = [], {}
    coverage = {'history_files': len(records), 'with_pre_round': 0, 'with_target_round': 0, 'missing_price': 0, 'missing_actual': 0}
    for p, rows in records:
        past = [r for r in rows if int(r['gameweekOrder']) < week]
        target = next((r for r in rows if int(r['gameweekOrder']) == week), None)
        if target is not None:
            coverage['with_target_round'] += 1
            actual[str(p['id'])] = number(target.get('points'))
        if not past:
            continue
        coverage['with_pre_round'] += 1
        price = next((number(r.get('cost')) for r in reversed(past) if number(r.get('cost')) is not None), None)
        if price is None:
            coverage['missing_price'] += 1
            continue
        pool.append({'id': p['id'], 'name': p['name'], 'team': p['team'], 'position': p['position'],
                     'price': price, 'xpts': project(p, past, config),
                     'previous_round_points': number(past[-1].get('points'), 0),
                     'actual_points': actual.get(str(p['id']))})
    return pool, actual, coverage


def evaluate_week(records, week, config, optimizer=None):
    if optimizer is None:
        from analysis.optimizer import optimize
        optimizer = optimize
    pool, actual, coverage = build_week(records, week, config)
    if len(pool) < 15:
        raise ValueError(f'{week}. hafta: yeterli oyuncu bulunamadı ({len(pool)})')
    result = optimizer(pool)
    if 'error' in result:
        raise ValueError(f'{week}. hafta: {result["error"]}')
    xi = result['starting_xi']
    captain_id = str(result['captain']['id'])
    missing = [p['id'] for p in xi if actual.get(str(p['id'])) is None]
    actual_score = None if missing else round(sum(actual[str(p['id'])] * (2 if str(p['id']) == captain_id else 1) for p in xi), 2)
    predicted = result['expected_points']
    return {'week': week, 'formation': result['formation'], 'captain': result['captain']['name'],
            'predicted': predicted, 'actual': actual_score,
            'error': None if actual_score is None else round(actual_score - predicted, 2),
            'absolute_error': None if actual_score is None else round(abs(actual_score-predicted), 2),
            'budget': result['squad_cost'], 'eligible_players': len(pool), 'coverage': coverage,
            'missing_actual_ids': missing,
            'starting_xi': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                             'xpts': p['xpts'], 'actual_points': actual.get(str(p['id'])),
                             'captain': str(p['id']) == captain_id} for p in xi],
            'bench': [{'id': p['id'], 'name': p['name'], 'position': p['position'],
                       'xpts': p['xpts'], 'actual_points': actual.get(str(p['id']))}
                      for p in result['squad'] if p['id'] not in {x['id'] for x in xi}],
            'formation_comparison': result['formation_comparison']}


def compare(records, train_rounds=(5,6,7,8), test_round=9, models=None, optimizer=None):
    models = models or MODELS
    if not train_rounds or any(w < 2 for w in train_rounds) or test_round <= max(train_rounds):
        raise ValueError('Test haftası bütün eğitim haftalarından sonra olmalı (min hafta 2).')
    results = {}
    for name, config in models.items():
        weeks = []
        for week in train_rounds:
            print(f'  {name}: hafta {week}', flush=True)
            weeks.append(evaluate_week(records, week, config, optimizer))
        valid = [w for w in weeks if w['actual'] is not None]
        if len(valid) != len(weeks):
            raise ValueError(f'{name}: bazı eğitim haftalarının gerçek puanları eksik; model seçimi yapılamaz')
        results[name] = {'config': config, 'training_weeks': weeks,
                         'training_mae': round(mean(w['absolute_error'] for w in valid), 3),
                         'training_mean_actual': round(mean(w['actual'] for w in valid), 3),
                         'training_mean_predicted': round(mean(w['predicted'] for w in valid), 3)}
    # Optimize for minimizing prediction error. Actual points is only a secondary tie breaker.
    best_name = min(results, key=lambda name: (results[name]['training_mae'], -results[name]['training_mean_actual']))
    print(f'Seçilen model: {best_name} (yalnızca eğitim haftalarına göre)', flush=True)
    holdout = evaluate_week(records, test_round, models[best_name], optimizer)
    return {'created_utc': datetime.now(timezone.utc).isoformat(),
            'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'train_rounds': list(train_rounds), 'holdout_round': test_round,
            'selection_rule': 'lowest mean absolute weekly team-score prediction error on training rounds; tie-break higher realized points',
            'selected_model': best_name, 'models': results, 'holdout': holdout,
            'limitations': [
                'Historical availability/suspensions and complete historic player pool are not verified.',
                'Historical prices are the latest recorded price before each target week; deadline prices are unverified.',
                'Historical FDR, bookmaker odds, and xgEdge forecasts are not reconstructed.',
                'No automatic substitutions, chips, or transfer penalties.',
                'This is a retrospective model comparison, not a verified point-in-time simulation.',
                'A single held-out round is insufficient to establish generalization.'
            ]}


def save_report(report, store=STORE):
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    json_path = store / f'multiweek_backtest_gw{report["holdout_round"]}.json'
    csv_path = store / f'multiweek_backtest_gw{report["holdout_round"]}.csv'
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['model', 'week', 'dataset', 'formation', 'captain', 'predicted', 'actual', 'error', 'absolute_error', 'budget'])
        writer.writeheader()
        for name, result in report['models'].items():
            for week in result['training_weeks']:
                writer.writerow({k: (name if k == 'model' else 'train' if k == 'dataset' else week.get(k)) for k in writer.fieldnames})
        week = report['holdout']
        writer.writerow({k: (report['selected_model'] if k == 'model' else 'holdout' if k == 'dataset' else week.get(k)) for k in writer.fieldnames})
    return json_path, csv_path


def main():
    parser = argparse.ArgumentParser(description='TFF walk-forward multiweek retrospective backtest')
    parser.add_argument('--collect', action='store_true', help='Fetch historical player data')
    parser.add_argument('--force', action='store_true', help='Refetch existing player histories')
    parser.add_argument('--train-rounds', type=int, nargs='+', default=[5,6,7,8])
    parser.add_argument('--test-round', type=int, default=9)
    args = parser.parse_args()
    if args.collect:
        collect(force=args.force)
    records = load_history()
    print(f'{len(records)} oyuncu geçmişi bulundu.')
    report = compare(records, tuple(args.train_rounds), args.test_round)
    json_path, csv_path = save_report(report)
    print('\nEğitim karşılaştırması (ortalama mutlak puan hatası):')
    for name, entry in sorted(report['models'].items(), key=lambda kv: kv[1]['training_mae']):
        print(f"  {name}: MAE={entry['training_mae']:.2f}, gerçek ortalama={entry['training_mean_actual']:.2f}")
    holdout = report['holdout']
    print(f"\nBAĞIMSIZ {args.test_round}. HAFTA: {report['selected_model']} | {holdout['formation']} | kaptan: {holdout['captain']}")
    print(f"Tahmin: {holdout['predicted']}, gerçek: {holdout['actual']}, hata: {holdout['error']}")
    print(f'JSON: {json_path}\nCSV: {csv_path}')


if __name__ == '__main__':
    main()
