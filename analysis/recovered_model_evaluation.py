"""Retrospective form-kernel comparison using only prior-week official position evidence."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analysis.multiweek_backtest import MODELS, project
from analysis.player_level_walkforward import (_load_records, _metric, _paired_difference,
    _fixture_teams, baseline_predictions, valid_row, BASELINES, MIN_HISTORY)
from analysis.recovered_history import _read_verified
from data_sources.historical_recovery import OUTPUT

STORE = Path('historical_data')


def _positions_for_week(position_evidence, week, source_policy='combined'):
    """Target-week and later dream teams are forbidden prediction inputs."""
    if source_policy not in ('official_only', 'combined'):
        raise ValueError('Unknown historical position source policy')
    positions = {}
    conflicts = set()
    for pid, rows in position_evidence['players'].items():
        prior = [row for row in rows if isinstance(row.get('effective_gameweek'), int)
                 and row['effective_gameweek'] < week and
                 (source_policy == 'combined' or str(row.get('quality') or '').startswith('official_'))]
        values = {row.get('position') for row in prior}
        if len(values) == 1 and next(iter(values)) in ('GK', 'DEF', 'MID', 'FWD'):
            positions[pid] = {'position': next(iter(values)),
                              'source_effective_week': max(row['effective_gameweek'] for row in prior),
                              'source_url': prior[-1]['source_url'],
                              'retrieved_at': prior[-1]['retrieved_at'],
                              'quality': prior[-1].get('quality')}
        elif len(values) > 1:
            conflicts.add(pid)
    return positions, conflicts


def _metric_with_coverage(rows, valid_targets, seed):
    result = _metric(rows, seed=seed)
    result['target_coverage'] = round(result['n']/valid_targets, 4) if valid_targets else None
    return result


def forecast_with_prior_position(position, past, target_week, model):
    """Exact existing form model, guarded against target/future-week rows."""
    if model not in MODELS or position not in ('GK', 'DEF', 'MID', 'FWD'):
        raise ValueError('Unknown model or historical fantasy position')
    if len(past) < MIN_HISTORY[model] or any(not isinstance(row.get('gameweekOrder'), int)
        or row['gameweekOrder'] >= target_week for row in past):
        raise ValueError('Insufficient or future player history')
    return project({'position': position}, past, MODELS[model])


def evaluate(store=STORE, recovered=OUTPUT, *, source_policy='combined'):
    store, recovered = Path(store), Path(recovered)
    recovery = json.loads((recovered/'coverage_report.json').read_text(encoding='utf-8'))
    manifest = json.loads((recovered/'official_collection_manifest.json').read_text(encoding='utf-8'))
    position_record = recovery['position_evidence']
    position_path = recovered/position_record['path']
    import hashlib
    if hashlib.sha256(position_path.read_bytes()).hexdigest() != position_record['sha256']:
        raise ValueError('Position evidence digest mismatch')
    position_evidence = json.loads(position_path.read_text(encoding='utf-8'))
    fixture_raw = _read_verified(recovered, manifest, 'fixtures_current')
    fixtures = {int(item['order']): {'gameweek_id': item['id'], 'matches': item['matches']}
                for item in fixture_raw['data']['gameweeks'] if isinstance(item,dict)
                and isinstance(item.get('order'),int)}
    records = _load_records(store)
    weekly = []
    cumulative_rows = {name: {'unconditional': [], 'appearance': []}
                       for name in (*MODELS, *BASELINES)}
    common_all_rows = {name: {'unconditional': [], 'appearance': []}
                       for name in (*MODELS, *BASELINES)}
    for week in range(2, 10):
        fixture = fixtures.get(week) or {}
        positions, conflicts = _positions_for_week(position_evidence, week, source_policy)
        active = [name for name in MODELS if week-1 >= MIN_HISTORY[name]]
        required = max((MIN_HISTORY[name] for name in active), default=None)
        rows_by_name = {name: {'unconditional': [], 'appearance': []}
                        for name in (*MODELS, *BASELINES)}
        excluded = Counter()
        valid_targets = 0
        if _fixture_teams(fixture) is not None:
            for pid, history in sorted(records.items(), key=lambda x: int(x[0])):
                target = [row for row in history if isinstance(row,dict) and row.get('gameweekOrder') == week]
                if len(target) != 1 or not valid_row(target[0], week, fixture)[0]:
                    excluded['missing_or_invalid_actual'] += 1
                    continue
                valid_targets += 1
                if not active:
                    continue
                if pid not in positions:
                    excluded['position_conflict' if pid in conflicts else 'no_prior_position'] += 1
                    continue
                past = [row for row in history if isinstance(row,dict) and
                        isinstance(row.get('gameweekOrder'),int) and row['gameweekOrder'] < week]
                if len(past) < required or len({row['gameweekOrder'] for row in past}) != len(past):
                    excluded['insufficient_or_duplicate_history'] += 1
                    continue
                if any(not valid_row(row, row['gameweekOrder'], fixtures.get(row['gameweekOrder']) or {})[0]
                       for row in past):
                    excluded['invalid_prior_result'] += 1
                    continue
                predictions = baseline_predictions(past, week)
                predictions.update({name: forecast_with_prior_position(
                    positions[pid]['position'], past, week, name) for name in active})
                for name, predicted in predictions.items():
                    item = {'week': week, 'player_id': pid, 'predicted': predicted,
                            'actual': target[0]['points'], 'played': target[0]['played'],
                            'position': positions[pid]['position'],
                            'position_source_effective_week': positions[pid]['source_effective_week']}
                    rows_by_name[name]['unconditional'].append(item)
                    cumulative_rows[name]['unconditional'].append(item)
                    if target[0]['played']:
                        rows_by_name[name]['appearance'].append(item)
                        cumulative_rows[name]['appearance'].append(item)
                    if len(active) == len(MODELS):
                        common_all_rows[name]['unconditional'].append(item)
                        if target[0]['played']:
                            common_all_rows[name]['appearance'].append(item)
        metrics = {}
        for name in (*MODELS, *BASELINES):
            if name in MODELS and name not in active:
                metrics[name] = {'status': 'not_evaluable', 'reason': 'minimum_history_not_met',
                                 'minimum_prior_weeks': MIN_HISTORY[name],
                                 'unconditional': _metric([]), 'appearance': _metric([])}
            elif rows_by_name[name]['unconditional']:
                metrics[name] = {'status': 'retrospective_reconstruction_form_component',
                    'unconditional': _metric_with_coverage(rows_by_name[name]['unconditional'],
                                                           valid_targets, week),
                    'appearance': _metric(rows_by_name[name]['appearance'], seed=week)}
            else:
                metrics[name] = {'status': 'not_evaluable', 'reason': 'no_valid_matched_sample',
                                 'unconditional': _metric([]), 'appearance': _metric([])}
        weekly.append({'week': week, 'classification': 'retrospective_not_predeadline_verified',
                       'available_models': active, 'minimum_prior_weeks_common_sample': required,
                       'prior_position_ids': len(positions), 'position_conflicts': len(conflicts),
                       'prior_official_position_ids': sum(str(p.get('quality') or '').startswith('official_')
                                                          for p in positions.values()),
                       'prior_third_party_position_ids': sum(str(p.get('quality') or '').startswith('third_party_')
                                                             for p in positions.values()),
                       'valid_target_results': valid_targets, 'excluded': dict(excluded),
                       'models': metrics})
    cumulative = {}
    for name in (*MODELS, *BASELINES):
        cumulative[name] = {'status': ('retrospective_reconstruction_form_component'
                                       if cumulative_rows[name]['unconditional'] else 'not_evaluable'),
            'unconditional': _metric(cumulative_rows[name]['unconditional']),
            'appearance': _metric(cumulative_rows[name]['appearance']),
            'weeks_evaluated': [r['week'] for r in weekly if r['models'][name]['unconditional']['n'] > 0],
            'sample_warning': 'Different weeks/model-history minima; do not rank from this table.'}
    matched = {name: {'unconditional': _metric(common_all_rows[name]['unconditional']),
                      'appearance': _metric(common_all_rows[name]['appearance'])}
               for name in (*MODELS, *BASELINES)}
    matched_weeks = [r['week'] for r in weekly if len(r['available_models']) == len(MODELS)
                     and r['models']['short_form_3w']['unconditional']['n'] > 0]
    lengths = {m['unconditional']['n'] for m in matched.values()}
    if len(lengths) != 1:
        raise ValueError('All-model comparison samples differ')
    ranking_mae = sorted(matched, key=lambda name: (
        matched[name]['unconditional']['mae'] if matched[name]['unconditional']['mae'] is not None else float('inf'), name))
    ranking_rmse = sorted(matched, key=lambda name: (
        matched[name]['unconditional']['rmse'] if matched[name]['unconditional']['rmse'] is not None else float('inf'), name))
    comparisons = {name: _paired_difference(common_all_rows[name]['unconditional'],
                                           common_all_rows['recent_3_average']['unconditional'])
                   for name in MODELS}
    return {'classification': 'retrospective_form_component_only_not_predeadline_verified',
            'source_policy': source_policy,
            'position_source': recovery['position_evidence'],
            'position_unique_ids': recovery['position_unique_player_ids'],
            'position_conflicts': recovery['position_conflicts'],
            'minimum_history': MIN_HISTORY, 'by_gameweek': weekly,
            'cumulative_unmatched_do_not_rank': cumulative,
            'matched_all_models': {'weeks': matched_weeks, 'n': next(iter(lengths)),
                                   'models': matched, 'ranking_by_mae': ranking_mae,
                                   'ranking_by_rmse': ranking_rmse,
                                   'paired_mae_vs_recent_3': comparisons},
            'limitations': ['This evaluates project() form kernels, not final fixture- and availability-adjusted /lineup forecasts.',
                            'Official-only positions come from strictly earlier dream teams, but were retrieved after old deadlines.',
                            'Official-only dream-team selection biases its sample toward previously high-scoring players.',
                            'Combined sensitivity additionally uses a third-party preseason workbook matched by unique name and official GW1 club; its commit author date does not prove push time.',
                            'No current position, club, price, availability or target-week dream-team data enters forecasts.',
                            'GW9 is the only week with eight prior rounds for stable_8w; one week cannot establish superiority.',
                            'Player-cluster bootstrap intervals do not capture every shared-match or gameweek shock.']}


def save_report(report, recovered=OUTPUT, *, suffix=''):
    recovered = Path(recovered)
    recovered.mkdir(parents=True, exist_ok=True)
    detailed = recovered/f'model_evaluation{suffix}.json'
    weekly = recovered/f'model_evaluation{suffix}.csv'
    cumulative = recovered/f'model_cumulative{suffix}_matched.csv'
    detailed.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    fields = ('week','model','target','status','n','mae','rmse','bias','mae_ci_95',
              'target_coverage','prior_position_ids','valid_target_results','reason')
    with weekly.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        for week in report['by_gameweek']:
            for name,item in week['models'].items():
                for target in ('unconditional','appearance'):
                    metric=item[target]
                    writer.writerow({'week':week['week'],'model':name,'target':target,
                        'status':item['status'],'n':metric['n'] if item['status'].startswith('retrospective') else '',
                        'mae':metric['mae'],'rmse':metric['rmse'],'bias':metric['bias'],
                        'mae_ci_95':json.dumps(metric['mae_ci_95']) if metric['mae_ci_95'] else '',
                        'target_coverage':metric.get('target_coverage'),
                        'prior_position_ids':week['prior_position_ids'],
                        'valid_target_results':week['valid_target_results'],
                        'reason':item.get('reason')})
    with cumulative.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=('model','target','n','mae','rmse','bias','mae_ci_95'))
        writer.writeheader()
        for name,item in report['matched_all_models']['models'].items():
            for target in ('unconditional','appearance'):
                metric=item[target]
                writer.writerow({'model':name,'target':target,'n':metric['n'],
                    'mae':metric['mae'],'rmse':metric['rmse'],'bias':metric['bias'],
                    'mae_ci_95':json.dumps(metric['mae_ci_95']) if metric['mae_ci_95'] else ''})
    return weekly,cumulative,detailed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Retrospective official-position form-model evaluation')
    parser.add_argument('--store',type=Path,default=STORE)
    parser.add_argument('--recovered',type=Path,default=OUTPUT)
    args=parser.parse_args()
    official=evaluate(args.store,args.recovered,source_policy='official_only')
    official_paths=save_report(official,args.recovered)
    combined=evaluate(args.store,args.recovered,source_policy='combined')
    combined_paths=save_report(combined,args.recovered,suffix='_combined')
    print(json.dumps({'official_only':{'matched_weeks':official['matched_all_models']['weeks'],
                                      'matched_n':official['matched_all_models']['n'],
                                      'ranking_by_mae':official['matched_all_models']['ranking_by_mae']},
                      'combined_sensitivity':{'matched_weeks':combined['matched_all_models']['weeks'],
                                              'matched_n':combined['matched_all_models']['n'],
                                              'ranking_by_mae':combined['matched_all_models']['ranking_by_mae']},
                      'files':[str(p) for p in (*official_paths,*combined_paths)]},indent=2))
