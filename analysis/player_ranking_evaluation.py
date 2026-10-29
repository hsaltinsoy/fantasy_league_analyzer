"""GW4–GW9 retrospective player ranking, separate from squad optimization."""
import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from analysis.multiweek_backtest import MODELS
from analysis.player_level_walkforward import (_fixture_teams, _load_records,
    baseline_predictions, valid_row, BASELINES, MIN_HISTORY)
from analysis.recovered_history import _read_verified
from analysis.recovered_model_evaluation import (_positions_for_week,
    forecast_with_prior_position)
from data_sources.historical_recovery import OUTPUT

STORE = Path('historical_data')
MODEL_NAMES = (*MODELS, *BASELINES)
METRIC_NAMES = ('spearman', 'precision_at_10', 'precision_at_20',
                'recall_at_20', 'ndcg_at_20')


def _average_ranks(values):
    """Descending average ranks, including ties."""
    order = sorted(range(len(values)), key=lambda i: -values[i])
    result = [None] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        rank = (start + 1 + stop) / 2
        for i in order[start:stop]:
            result[i] = rank
        start = stop
    return result


def _top_weights(values, cutoff):
    """Fractionally allocate cutoff slots across equal-score boundary ties."""
    order = sorted(range(len(values)), key=lambda i: -values[i])
    result = [0.] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        share = max(0., min(stop, cutoff) - start) / (stop - start)
        for i in order[start:stop]:
            result[i] = share
        start = stop
    return result


def _ndcg(predicted, actual, cutoff=20):
    gains = [max(0., value) for value in actual]
    ideal = sum(gain / math.log2(rank + 2)
                for rank, gain in enumerate(sorted(gains, reverse=True)[:cutoff]))
    if ideal <= 0:
        return None
    order = sorted(range(len(predicted)), key=lambda i: -predicted[i])
    dcg = 0.
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and predicted[order[stop]] == predicted[order[start]]:
            stop += 1
        # A predicted-score tie is a uniform random order within its group.
        mean_discount = sum(1 / math.log2(rank + 2) for rank in range(start, min(stop, cutoff))) / (stop-start)
        dcg += mean_discount * sum(gains[i] for i in order[start:stop])
        start = stop
    return dcg / ideal


def ranking_metrics(rows, model):
    """Score a fixed candidate sample; actuals never enter forecast functions."""
    ids = [str(row['player_id']) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate player in ranking sample')
    if any(model not in row['predictions'] or not isinstance(row.get('actual'), (int, float))
           or not isinstance(row['predictions'].get(model), (int, float))
           or not math.isfinite(row['actual']) or not math.isfinite(row['predictions'][model])
           for row in rows):
        raise ValueError('Incomplete or invalid matched ranking sample')
    n = len(rows)
    output = {'n': n, **{name: None for name in METRIC_NAMES},
              'actual_tie_at_10': False, 'actual_tie_at_20': False,
              'predicted_tie_at_10': False, 'predicted_tie_at_20': False}
    if not n:
        return output
    predicted = [row['predictions'][model] for row in rows]
    actual = [row['actual'] for row in rows]
    rank_p, rank_a = _average_ranks(predicted), _average_ranks(actual)
    center = (n+1)/2
    covariance = sum((p-center)*(a-center) for p,a in zip(rank_p,rank_a))
    variance_p = sum((p-center)**2 for p in rank_p)
    variance_a = sum((a-center)**2 for a in rank_a)
    if n >= 3 and variance_p > 0 and variance_a > 0:
        output['spearman'] = round(covariance/math.sqrt(variance_p*variance_a), 4)
    for cutoff in (10,20):
        if n < cutoff:
            continue
        pw, aw = _top_weights(predicted, cutoff), _top_weights(actual, cutoff)
        overlap = sum(p*a for p,a in zip(pw,aw))
        output[f'precision_at_{cutoff}'] = round(overlap/cutoff, 4)
        output[f'actual_tie_at_{cutoff}'] = any(0 < value < 1 for value in aw)
        output[f'predicted_tie_at_{cutoff}'] = any(0 < value < 1 for value in pw)
        if cutoff == 20:
            # Both top-20 sets have twenty places, so recall@20 equals P@20.
            output['recall_at_20'] = round(overlap/sum(aw), 4)
            ndcg = _ndcg(predicted, actual)
            output['ndcg_at_20'] = round(ndcg, 4) if ndcg is not None else None
    return output


def _bootstrap_interval(rows, model, metric, *, seed=13, replicates=250):
    if len(rows) < 10:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(replicates):
        draw = [dict(rows[rng.randrange(len(rows))], player_id=str(index))
                for index in range(len(rows))]
        value = ranking_metrics(draw, model)[metric]
        if value is not None:
            values.append(value)
    if len(values) < replicates//2:
        return None
    values.sort()
    return [values[int(.025*(len(values)-1))], values[int(.975*(len(values)-1))]]


def _paired_interval(rows, model, baseline, metric, *, seed=29, replicates=250):
    if len(rows) < 20:
        return None
    point_a = ranking_metrics(rows, model)[metric]
    point_b = ranking_metrics(rows, baseline)[metric]
    if point_a is None or point_b is None:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(replicates):
        draw = [dict(rows[rng.randrange(len(rows))], player_id=str(index))
                for index in range(len(rows))]
        a, b = ranking_metrics(draw, model)[metric], ranking_metrics(draw, baseline)[metric]
        if a is not None and b is not None:
            values.append(a-b)
    if len(values) < replicates//2:
        return None
    values.sort()
    return {'difference': round(point_a-point_b, 4),
            'player_bootstrap_ci_95': [round(values[int(.025*(len(values)-1))],4),
                                       round(values[int(.975*(len(values)-1))],4)]}


def _load_inputs(store, recovered):
    recovery = json.loads((recovered/'coverage_report.json').read_text(encoding='utf-8'))
    manifest = json.loads((recovered/'official_collection_manifest.json').read_text(encoding='utf-8'))
    evidence_entry = recovery['position_evidence']
    raw = (recovered/evidence_entry['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence_entry['sha256']:
        raise ValueError('Recovered position evidence digest mismatch')
    positions = json.loads(raw)
    fixture_raw = _read_verified(recovered, manifest, 'fixtures_current')
    fixtures = {int(item['order']): {'gameweek_id': item['id'], 'matches': item['matches']}
                for item in fixture_raw['data']['gameweeks'] if isinstance(item,dict)
                and isinstance(item.get('order'),int)}
    return recovery, positions, fixtures, _load_records(store)


def _week_samples(week, positions_evidence, fixtures, records, source_policy):
    """Build forecasts from prior data; load target row afterward for evaluation."""
    positions, conflicts = _positions_for_week(positions_evidence, week, source_policy)
    active = [name for name in MODELS if week-1 >= MIN_HISTORY[name]]
    required = max((MIN_HISTORY[name] for name in active), default=None)
    fixture = fixtures.get(week) or {}
    if _fixture_teams(fixture) is None:
        return {'week': week, 'active_models': active, 'required_history': required,
                'position_ids': len(positions), 'excluded': {'invalid_fixture': 1},
                'all': [], 'appearance': []}
    all_rows, appeared = [], []
    excluded = defaultdict(int)
    for pid, history in sorted(records.items(), key=lambda pair: int(pair[0])):
        if not active or pid not in positions:
            excluded['no_active_model_or_prior_position'] += 1
            continue
        past = [row for row in history if isinstance(row,dict) and
                isinstance(row.get('gameweekOrder'),int) and row['gameweekOrder'] < week]
        if len(past) < required or len({r['gameweekOrder'] for r in past}) != len(past):
            excluded['insufficient_or_duplicate_history'] += 1
            continue
        if any(not valid_row(row, row['gameweekOrder'], fixtures.get(row['gameweekOrder']) or {})[0]
               for row in past):
            excluded['invalid_past_result'] += 1
            continue
        # No target-week row or Team of the Week is passed to either predictor.
        forecasts = baseline_predictions(past, week)
        forecasts.update({name: forecast_with_prior_position(positions[pid]['position'],
                                                             past, week, name) for name in active})
        target = [row for row in history if isinstance(row,dict) and row.get('gameweekOrder') == week]
        if len(target) != 1 or not valid_row(target[0], week, fixture)[0]:
            excluded['missing_or_invalid_target_result'] += 1
            continue
        item = {'player_id': pid, 'week': week, 'predictions': forecasts,
                'actual': target[0]['points'], 'played': target[0]['played'],
                'position_source_effective_week': positions[pid]['source_effective_week']}
        all_rows.append(item)
        if item['played']:
            appeared.append(item)
    return {'week': week, 'active_models': active, 'required_history': required,
            'position_ids': len(positions), 'position_conflicts': len(conflicts),
            'excluded': dict(excluded), 'all': all_rows, 'appearance': appeared}


def evaluate(store=STORE, recovered=OUTPUT, *, source_policy='official_only'):
    store, recovered = Path(store), Path(recovered)
    recovery, positions, fixtures, records = _load_inputs(store, recovered)
    previous_report_path = recovered/('model_evaluation.json' if source_policy=='official_only'
                                      else 'model_evaluation_combined.json')
    previous = json.loads(previous_report_path.read_text(encoding='utf-8')) if previous_report_path.exists() else None
    weekly = []
    rows_for_gw9 = None
    for week in range(4,10):
        sample = _week_samples(week, positions, fixtures, records, source_policy)
        if previous:
            expected = previous['by_gameweek'][week-2]['models']['short_form_3w']['unconditional']['n']
            if len(sample['all']) != expected:
                raise ValueError(f'GW{week}: ranking and Phase 12 forecasting samples differ')
        models = [*sample['active_models'], *BASELINES]
        metrics = {target: {name: ranking_metrics(sample[rows_key], name)
                            for name in models}
                   for target, rows_key in (('all','all'),('appeared','appearance'))}
        weekly.append({'week': week, 'status': 'retrospective_reconstruction' if sample['all'] else 'not_evaluable',
                       'active_models': sample['active_models'], 'position_ids': sample['position_ids'],
                       'sample_n': len(sample['all']), 'appeared_n': len(sample['appearance']),
                       'excluded': sample['excluded'], 'metrics': metrics})
        if week == 9:
            rows_for_gw9 = sample
    common = rows_for_gw9 or {'all': [], 'appearance': []}
    gw9 = {}
    for target, rows_key in (('all','all'),('appeared','appearance')):
        rows = common[rows_key]
        gw9[target] = {name: ranking_metrics(rows,name) for name in MODEL_NAMES}
        for name in MODEL_NAMES:
            gw9[target][name]['spearman_player_ci_95'] = _bootstrap_interval(rows,name,'spearman',seed=9)
            gw9[target][name]['precision_at_20_player_ci_95'] = _bootstrap_interval(rows,name,'precision_at_20',seed=19)
            gw9[target][name]['ndcg_at_20_player_ci_95'] = _bootstrap_interval(rows,name,'ndcg_at_20',seed=29)
    paired = {name: {metric: _paired_interval(common['all'],name,'recent_3_average',metric)
                     for metric in ('spearman','precision_at_20','ndcg_at_20')}
              for name in MODELS}
    mae_vs_ranking = {
        name: {'mae': previous['matched_all_models']['models'][name]['unconditional']['mae'],
               'spearman': gw9['all'][name]['spearman'],
               'precision_at_20': gw9['all'][name]['precision_at_20'],
               'ndcg_at_20': gw9['all'][name]['ndcg_at_20']}
        for name in MODEL_NAMES} if previous else None
    return {'classification': 'retrospective_ranking_not_predeadline_verified',
            'source_policy': source_policy, 'source_quality':
            ('official_historical_dream_team_only' if source_policy=='official_only'
             else 'official_plus_lower_confidence_third_party_workbook'),
            'metric_definitions': {
                'universe': 'Only matched player-week rows with valid prior statistics and position evidence.',
                'top_performers': 'Highest target-week fantasy points within the evaluated weekly sample.',
                'spearman': 'Pearson correlation of descending average ranks for ties; undefined for constant scores.',
                'precision_recall': 'Fractional cutoff ties for both forecasts and actuals. Both top-20 sets have 20 slots, so P@20 equals Recall@20.',
                'ndcg': 'NDCG@20 with nonnegative actual fantasy points as linear gain; predicted ties share discount positions.',
                'small_samples': 'Top-K metrics unavailable if sample has fewer than K players.',
                'uncertainty': 'GW9 percentile bootstrap over players (250 resamples), conditional on this one week; does not measure across-week uncertainty.'},
            'by_gameweek': weekly, 'gw9_matched': {'week': 9, 'all_n': len(common['all']),
                'appeared_n': len(common['appearance']), 'metrics': gw9,
                'paired_vs_recent_3': paired},
            'gw9_mae_vs_ranking': mae_vs_ranking,
            'limitations': ['Positions are retrospective; official-only sample is selected by earlier dream-team membership.',
                            'Combined tier additionally uses a lower-confidence preseason workbook identity join.',
                            'Appeared-only ranking conditions on a target-week outcome and is diagnostic, not a predeadline selection rule.',
                            'One GW9 sample cannot identify a winning model or imply better fantasy squad selection.'],
            'recovery_coverage_path': 'coverage_report.json'}


def save_report(report, recovered=OUTPUT):
    recovered = Path(recovered)
    suffix = 'official' if report['source_policy']=='official_only' else 'combined'
    json_path = recovered/f'player_ranking_{suffix}.json'
    csv_path = recovered/f'player_ranking_{suffix}.csv'
    json_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    columns = ('week','sample','model','n',*METRIC_NAMES)
    with csv_path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=columns)
        writer.writeheader()
        for week in report['by_gameweek']:
            for sample, metrics in week['metrics'].items():
                for name, value in metrics.items():
                    writer.writerow({'week':week['week'],'sample':sample,'model':name,
                                     **{key:value[key] for key in ('n',*METRIC_NAMES)}})
    return json_path,csv_path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='GW4-GW9 retrospective player-ranking evaluation')
    parser.add_argument('--store',type=Path,default=STORE)
    parser.add_argument('--recovered',type=Path,default=OUTPUT)
    args=parser.parse_args()
    for policy in ('official_only','combined'):
        report=evaluate(args.store,args.recovered,source_policy=policy)
        paths=save_report(report,args.recovered)
        print(json.dumps({'source_policy':policy,'gw9_all_n':report['gw9_matched']['all_n'],
                          'gw9_appeared_n':report['gw9_matched']['appeared_n'],
                          'files':[str(p) for p in paths]},indent=2))
