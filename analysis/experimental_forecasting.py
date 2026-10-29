"""Opt-in retrospective ridge experiment; never writes live prediction records."""
import argparse
import json
import math
from pathlib import Path
from statistics import mean

from analysis.player_level_walkforward import _metric
from analysis.player_ranking_evaluation import (_load_inputs, _week_samples,
    ranking_metrics, _bootstrap_interval)
from analysis.recovered_model_evaluation import _positions_for_week
from analysis.multiweek_backtest import MODELS
from analysis.player_level_walkforward import BASELINES

NAME = 'experimental_rolling_ridge_v1'
BLEND = 'experimental_ridge_short_blend_v1'
FEATURES = ('points_3', 'points_5', 'points_8', 'points_season',
            'has_5_weeks', 'has_8_weeks',
            'minutes_3', 'appearance_3', 'goals_3', 'assists_3',
            'history_count', 'position_GK', 'position_DEF', 'position_MID', 'position_FWD')
POSITIONS = ('GK', 'DEF', 'MID', 'FWD')
MIN_TRAIN = 120
ALPHA = 100.0  # Fixed before evaluation; no target-week tuning.
GAP_WEEKS = 1


def build_features(past, target_week, position):
    """Only earlier player-week rows and independently supplied prior position."""
    if position not in POSITIONS or not isinstance(target_week, int):
        raise ValueError('Prior fantasy position and integer target week required')
    weeks = [r.get('gameweekOrder') for r in past]
    if len(weeks) < 3 or any(not isinstance(w, int) or w >= target_week for w in weeks) or len(set(weeks)) != len(weeks):
        raise ValueError('At least three unique prior weeks required; future rows forbidden')
    rows = sorted(past, key=lambda r: r['gameweekOrder'])
    for row in rows:
        if any(not isinstance(row.get(k), (int, float)) or isinstance(row[k], bool)
               or not math.isfinite(row[k]) for k in ('points', 'minutesPlayed')):
            raise ValueError('Prior points and minutes must be explicit finite numbers')
    def average(key, window):
        if len(rows) < window:
            return None
        sample = rows[-window:]
        values = [r.get(key) for r in sample]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in values):
            return None
        return mean(values)
    values = {
        'points_3': average('points', 3), 'points_5': average('points', 5),
        'points_8': average('points', 8), 'points_season': average('points', len(rows)),
        'has_5_weeks': float(len(rows) >= 5), 'has_8_weeks': float(len(rows) >= 8),
        'minutes_3': average('minutesPlayed', 3),
        'appearance_3': mean(float(r['minutesPlayed'] > 0) for r in rows[-3:]),
        'goals_3': average('goals', 3), 'assists_3': average('assists', 3),
        'history_count': min(len(rows), 8),
    }
    values.update({f'position_{name}': float(position == name) for name in POSITIONS})
    return values


def _solve(matrix, vector):
    """Small deterministic Gaussian solver with pivoting."""
    rows = [list(row) + [value] for row, value in zip(matrix, vector)]
    n = len(rows)
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(rows[i][col]))
        if abs(rows[pivot][col]) < 1e-10:
            raise ValueError('Singular regularized model')
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [v / scale for v in rows[col]]
        for other in range(n):
            if other != col:
                factor = rows[other][col]
                rows[other] = [a - factor*b for a, b in zip(rows[other], rows[col])]
    return [row[-1] for row in rows]


def fit_ridge(training, alpha=ALPHA):
    """Training-only imputation and scaling; unconditional fantasy points target."""
    if len(training) < MIN_TRAIN or not all(math.isfinite(row['actual']) for row in training):
        raise ValueError('Insufficient valid training rows')
    centers = {}
    scales = {}
    for name in FEATURES:
        values = [r['features'][name] for r in training if r['features'][name] is not None]
        if not values:
            centers[name], scales[name] = 0.0, 1.0
            continue
        centers[name] = mean(values)
        variance = mean((v-centers[name])**2 for v in values)
        scales[name] = math.sqrt(variance) if variance > 1e-12 else 1.0
    def vector(features):
        return [1.0] + [((features[name] if features[name] is not None else centers[name])-centers[name])/scales[name]
                        for name in FEATURES]
    vectors = [vector(r['features']) for r in training]
    size = len(FEATURES)+1
    gram = [[sum(v[i]*v[j] for v in vectors) + (alpha if i == j and i else 0.0)
             for j in range(size)] for i in range(size)]
    rhs = [sum(v[i]*r['actual'] for v, r in zip(vectors, training)) for i in range(size)]
    return {'coefficients': _solve(gram, rhs), 'centers': centers, 'scales': scales,
            'training_n': len(training), 'alpha': alpha}


def forecast(model, features):
    vector = [1.0] + [((features[name] if features[name] is not None else model['centers'][name])
                       -model['centers'][name])/model['scales'][name] for name in FEATURES]
    # The target is unconditional weekly points, so do not multiply by appearance probability.
    return max(0.0, sum(a*b for a, b in zip(model['coefficients'], vector)))


def evaluate(store=Path('historical_data'), recovered=Path('historical_data/recovered'), *, source_policy='official_only'):
    _, position_evidence, fixtures, records = _load_inputs(Path(store), Path(recovered))
    samples = {}
    for week in range(4, 10):
        sample = _week_samples(week, position_evidence, fixtures, records, source_policy)
        positions, _ = _positions_for_week(position_evidence, week, source_policy)
        enriched = []
        for row in sample['all']:
            past = [r for r in records[row['player_id']] if r['gameweekOrder'] < week]
            enriched.append({**row, 'features': build_features(past, week, positions[row['player_id']]['position'])})
        samples[week] = enriched
    results = []
    for target in range(6, 10):
        train_weeks = list(range(4, target-GAP_WEEKS))
        training = [row for week in train_weeks for row in samples[week]]
        test = samples[target]
        active = [*(_ for _ in MODELS if _ in (test[0]['predictions'] if test else {})), *BASELINES]
        if len(training) < MIN_TRAIN or len(train_weeks) < 2 or not test:
            results.append({'week': target, 'status': 'not_evaluable', 'training_n': len(training),
                            'test_n': len(test), 'sample_coverage': round(len(test)/len(records), 4) if records else None,
                            'reason': 'Insufficient earlier training weeks or rows'})
            continue
        model = fit_ridge(training)
        scored = []
        for row in test:
            ridge = forecast(model, row['features'])
            blend = (ridge + row['predictions']['short_form_3w']) / 2
            scored.append({**row, 'predictions': {**row['predictions'], NAME: ridge, BLEND: blend}})
        comparison = {}
        for name in (NAME, BLEND, *active):
            errors = [{'player_id': row['player_id'], 'predicted': row['predictions'][name], 'actual': row['actual']}
                      for row in scored]
            metrics = _metric(errors, replicates=150)
            ranks = ranking_metrics(scored, name)
            selected = sorted(scored, key=lambda r: (-r['predictions'][name], str(r['player_id'])))[:11]
            high = [r for r in scored if r['actual'] > 2]
            comparison[name] = {'n': metrics['n'], 'mae': metrics['mae'], 'rmse': metrics['rmse'],
                'bias': metrics['bias'], 'mae_ci_95': metrics['mae_ci_95'],
                'spearman': ranks['spearman'], 'precision_at_10': ranks['precision_at_10'],
                'precision_at_20': ranks['precision_at_20'], 'ndcg_at_20': ranks['ndcg_at_20'],
                'top_11_actual_points': round(sum(r['actual'] for r in selected), 3),
                'high_return_n': len(high),
                'high_return_mae': round(mean(abs(r['predictions'][name]-r['actual']) for r in high), 3) if high else None,
                'spearman_ci_95': _bootstrap_interval(scored, name, 'spearman', replicates=150)}
        results.append({'week': target, 'status': 'retrospective_reconstruction',
                        'training_weeks': train_weeks, 'training_n': len(training),
                        'test_n': len(test), 'sample_coverage': round(len(test)/len(records), 4) if records else None,
                        'appeared_n': sum(r['played'] for r in scored),
                        'models': comparison})
    return {'models': [NAME, BLEND], 'source_policy': source_policy, 'classification': 'retrospective_reconstruction',
            'horizon_gameweeks': 1, 'features': list(FEATURES), 'alpha': ALPHA,
            'minimum_training_rows': MIN_TRAIN, 'training_gap_gameweeks': GAP_WEEKS,
            'blend_weights': {NAME: 0.5, 'short_form_3w': 0.5},
            'high_return_definition': 'Actual target-week fantasy points greater than 2; retrospective diagnostic only.',
            'by_gameweek': results,
            'limitations': ['Position evidence is retrospective, not verified at historical deadlines.',
                'Official-only sample is selected by prior dream-team membership.',
                'Combined tier adds lower-confidence workbook positions.',
                'Training uses unconditional player-week points; no separate appearance multiplier.',
                'xG/xA, current clubs, current prices, and current availability are excluded.',
                'Target-week actuals define evaluation outcomes only, not forecast features.',
                'A small number of chronological weeks cannot establish future superiority.']}


def save_report(report, output=Path('historical_data/experimental_phase15')):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / ('ridge_official.json' if report['source_policy']=='official_only' else 'ridge_combined.json')
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--store', type=Path, default=Path('historical_data'))
    parser.add_argument('--recovered', type=Path, default=Path('historical_data/recovered'))
    args = parser.parse_args()
    for tier in ('official_only', 'combined'):
        report = evaluate(args.store, args.recovered, source_policy=tier)
        print(save_report(report))
