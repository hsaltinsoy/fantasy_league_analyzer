"""Evaluate saved production lineups without reconstructing unavailable inputs."""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

from analysis.prediction_tracking import DEFAULT_DB, connect, get_prediction


def actuals_for_week(week, store=Path('historical_data')):
    actual = {}
    for path in Path(store).glob('player_*.json'):
        player_id = path.stem.removeprefix('player_')
        rows = json.loads(path.read_text(encoding='utf-8'))
        target = [r for r in rows if isinstance(r, dict) and r.get('gameweekOrder') == week]
        if len(target) == 1 and target[0].get('points') is not None:
            actual[player_id] = float(target[0]['points'])
    return actual


def _metrics(errors):
    absolute = [abs(x) for x in errors]
    mae = mean(absolute) if absolute else None
    margin = 1.96 * stdev(absolute) / math.sqrt(len(absolute)) if len(absolute) >= 2 else None
    return {'n': len(errors), 'mae': round(mae, 3) if mae is not None else None,
            'rmse': round(math.sqrt(mean(x*x for x in errors)), 3) if errors else None,
            'approx_mae_interval_95pct': [round(max(0,mae-margin),3),round(mae+margin,3)] if margin is not None else None}


def evaluate_saved(prediction, snapshot, actual):
    payload = prediction['payload']
    xi = payload.get('starting_xi') or []
    if len(xi) != 11 or sum(bool(p.get('captain')) for p in xi) != 1:
        return {'status': 'not_evaluable', 'reason': 'incomplete_lineup'}
    source_players={str(p.get('id')):p for p in snapshot.get('players', [])}
    for selected in xi:
        source=source_players.get(str(selected['id']))
        if source is None:
            return {'status':'not_evaluable','reason':'player_missing_from_snapshot'}
        if source.get('price') is None or selected.get('price') is None:
            return {'status':'not_evaluable','reason':'missing_snapshot_price'}
        if str(source.get('club_id') or source.get('team')) != str(selected.get('team')):
            return {'status':'not_evaluable','reason':'player_transfer_or_club_mismatch'}
        if float(source['price']) != float(selected['price']):
            return {'status':'not_evaluable','reason':'price_mismatch'}
    official_fixtures={}
    for match in snapshot.get('fixtures', []):
        if 'homeClubId' in match and 'awayClubId' in match:
            official_fixtures[str(match['homeClubId'])]=str(match['awayClubId'])
            official_fixtures[str(match['awayClubId'])]=str(match['homeClubId'])
    if official_fixtures and any(official_fixtures.get(str(p['team'])) != str(p.get('opponent')) for p in xi):
        return {'status':'not_evaluable','reason':'incorrect_fixture_mapping'}
    by_id = {str(h['player_id']): h['rows'] for h in snapshot.get('histories', [])}
    if any(int(r['gameweekOrder']) >= prediction['gameweek'] for rows in by_id.values() for r in rows):
        return {'status':'not_evaluable','reason':'future_statistics_in_snapshot'}
    player_rows = []
    missing = []
    for p in xi:
        pid = str(p['id'])
        if pid not in actual:
            missing.append(pid)
            continue
        past = [r for r in by_id.get(pid, []) if int(r['gameweekOrder']) < prediction['gameweek']]
        values = [float(r['points']) for r in past if r.get('points') is not None]
        recent = mean(values[-3:]) if values else None
        season = mean(values) if values else None
        player_rows.append({'id': p['id'], 'predicted': float(p['xpts']), 'actual': actual[pid],
                            'error': actual[pid]-float(p['xpts']), 'captain': bool(p.get('captain')),
                            'recent_3_baseline': recent, 'season_to_date_baseline': season})
    if missing:
        return {'status': 'not_evaluable', 'reason': 'missing_actual_results',
                'missing_player_ids': missing, 'coverage': len(player_rows)/11}
    captain = next(p for p in player_rows if p['captain'])
    actual_xi = sum(p['actual'] for p in player_rows)
    actual_total = actual_xi + captain['actual']
    predicted = sum(p['predicted'] for p in player_rows) + captain['predicted']
    baseline = {}
    for label in ('recent_3_baseline', 'season_to_date_baseline'):
        if all(p[label] is not None for p in player_rows):
            baseline[label] = sum(p[label] for p in player_rows) + captain[label]
        else:
            baseline[label] = None
    quality = snapshot.get('data_quality') or {}
    return {'status': prediction['status'], 'gameweek': prediction['gameweek'],
            'model': prediction['model'], 'prediction_id': prediction['id'],
            'predicted_points': round(predicted,2), 'actual_points': round(actual_total,2),
            'error': round(actual_total-predicted,2), 'starting_xi_actual_points': round(actual_xi,2),
            'captain_contribution': round(captain['actual'],2),
            'formation': payload.get('formation'), 'squad_cost': payload.get('cost',payload.get('squad_cost')),
            'risk_adjusted_objective': prediction['risk_adjusted_objective'],
            'player_metrics': _metrics([p['error'] for p in player_rows]),
            'players': player_rows, 'baselines': baseline,
            'coverage': 1.0, 'missing_data_rate': quality.get('missing_statistics',0)/max(1,quality.get('total_tff_players',1)),
            'data_quality': quality}


def report(path=DEFAULT_DB, store=Path('historical_data')):
    path = Path(path)
    if not path.exists():
        return {'classification':'not_evaluable', 'reason':'No saved production predictions',
                'predictions':[], 'by_gameweek':{}, 'by_model':{}, 'counts':{'verified':0,'unverified':0},
                'limitations':['Historical archives alone cannot reproduce complete production predictions at the deadline.']}
    with connect(path) as db:
        ids = [r[0] for r in db.execute('SELECT id FROM predictions ORDER BY created_at,id')]
        snapshots = {r[0]:json.loads(r[1]) for r in db.execute('SELECT id,payload FROM snapshots')}
    rows=[]
    actual_cache={}
    for prediction_id in ids:
        prediction=get_prediction(prediction_id,path)
        week=prediction['gameweek']
        if week not in actual_cache:
            actual_cache[week]=actuals_for_week(week,store)
        rows.append(evaluate_saved(prediction,snapshots[prediction['snapshot_id']],actual_cache[week]) |
                    {'prediction_id':prediction_id,'verification_status':prediction['status'],
                     'gameweek':week,'model':prediction['model']})
    def groups(key):
        grouped=defaultdict(list)
        for row in rows: grouped[str(row[key])].append(row)
        output={}
        for group, items in grouped.items():
            scored=[x for x in items if x['status']!='not_evaluable']
            baseline_metrics={}
            for label in ('recent_3_baseline','season_to_date_baseline'):
                errors=[x['actual_points']-x['baselines'][label] for x in scored if x['baselines'][label] is not None]
                baseline_metrics[label]=_metrics(errors)
            output[group]={'predictions':len(items),'evaluable':len(scored),
                           'team_metrics':_metrics([x['error'] for x in scored]),
                           'baselines':baseline_metrics}
        return output
    verified=sum(r['verification_status']=='verified_pre_deadline' and r['status']!='not_evaluable' for r in rows)
    return {'classification':'mixed_evidence_do_not_pool_verified_and_unverified',
            'predictions':rows,'by_gameweek':groups('gameweek'),'by_model':groups('model'),
            'counts':{'verified':verified,'unverified':len(rows)-verified},
            'limitations':['Only saved production lineups are evaluated.',
                           'Actuals come from a later local archive; source completeness is not independently verified.',
                           'A small number of rounds gives unstable MAE and RMSE.',
                           'The displayed 95% MAE interval is a rough normal approximation, unsuitable for tiny samples.',
                           'Historical player clubs, prices and availability are not reconstructed.']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('historical_data/production_evaluation.json'))
    args=parser.parse_args()
    result=report()
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'counts':result['counts'],'by_gameweek':result['by_gameweek'],
                      'by_model':result['by_model']},ensure_ascii=False,indent=2))
