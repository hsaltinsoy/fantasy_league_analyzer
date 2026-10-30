"""Opt-in Phase 15 models on an existing immutable prospective snapshot."""
import hashlib
import json
import os
from pathlib import Path

from analysis.experimental_forecasting import (ALPHA, BLEND, FEATURES, GAP_WEEKS,
    MIN_TRAIN, NAME, build_features, fit_ridge, forecast)
from analysis.player_ranking_evaluation import _load_inputs, _week_samples
from analysis.prediction_tracking import get_snapshot, save_prediction_batch
from analysis.predict_next_week import build_candidate_pool
from analysis.live_benchmark import _fixture_lookup
from analysis.optimizer import optimize


MODEL_VERSION = 'phase15.ridge-v1'


def train_for_target(target_week, *, store=Path('historical_data'),
                     recovered=Path('historical_data/recovered'), source_policy='combined'):
    """Freeze a historical ridge fit using labels no later than target minus two."""
    if source_policy not in ('official_only', 'combined'):
        raise ValueError('Unknown historical evidence tier')
    if (os.environ.get('STORAGE_BACKEND', 'postgres').lower() == 'postgres'
            and Path(store) == Path('historical_data')
            and Path(recovered) == Path('historical_data/recovered')):
        from storage.db import engine_from_env
        from storage.runtime_repository import RuntimeRepository
        _, positions, fixtures, records, coverage_digest = (
            RuntimeRepository(engine_from_env()).phase15_training_inputs(target_week))
    else:
        _, positions, fixtures, records = _load_inputs(Path(store), Path(recovered))
        coverage_digest = hashlib.sha256((Path(recovered)/'coverage_report.json').read_bytes()).hexdigest()
    training = []
    weeks = list(range(4, min(9, target_week-GAP_WEEKS-1)+1))
    # For target N and one-week gap, the latest training label is N-2.
    for week in weeks:
        sample = _week_samples(week, positions, fixtures, records, source_policy)
        from analysis.recovered_model_evaluation import _positions_for_week
        prior_positions, _ = _positions_for_week(positions, week, source_policy)
        for row in sample['all']:
            past = [r for r in records[row['player_id']] if r['gameweekOrder'] < week]
            training.append({'features':build_features(past,week,prior_positions[row['player_id']]['position']),
                             'actual':row['actual']})
    if len(weeks) < 2 or len(training) < MIN_TRAIN:
        raise ValueError(f'Insufficient dated training observations: {len(training)} across {len(weeks)} weeks')
    fitted = fit_ridge(training)
    return fitted, {'source_policy':source_policy,'training_weeks':weeks,
                    'training_n':len(training),'gap_gameweeks':GAP_WEEKS,
                    'position_coverage_digest':coverage_digest,
                    'features':list(FEATURES),'alpha':ALPHA}


def save_variants(snapshot_id, *, path, store=Path('historical_data'),
                  recovered=Path('historical_data/recovered')):
    snapshot = get_snapshot(snapshot_id, path)
    if snapshot is None or snapshot['classification'] != 'live':
        raise ValueError('Live immutable snapshot required for experimental variants')
    week = snapshot['gameweek']
    fitted, training = train_for_target(week, store=store, recovered=recovered)
    payload = snapshot['payload']
    players = payload['players']
    histories = {str(h['player_id']):h['rows'] for h in payload['histories']}
    records = [(p, histories.get(str(p['id']), [])) for p in players]
    fixtures = {week:_fixture_lookup({'matches':payload['fixtures']})}
    pool, production_exclusions = build_candidate_pool(week, players, records, fixtures)
    predicted = []
    insufficient = 0
    for player in pool:
        past = histories.get(str(player['id']), [])
        if len(past) < 3:
            insufficient += 1
            continue
        features = build_features(past, week, player['position'])
        ridge = forecast(fitted, features)
        predicted.append((player, ridge))
    if len(predicted) < 15:
        raise ValueError(f'Only {len(predicted)} eligible players have three prior weeks; {insufficient} excluded')
    prepared = []
    for name in (NAME, BLEND):
        candidates = []
        for player, ridge in predicted:
            value = ridge if name == NAME else (ridge + float(player['xpts']))/2
            candidates.append({**player, 'xpts':round(value, 3)})
        solution = optimize(candidates, risk_profile='balanced')
        if 'error' in solution:
            raise ValueError(f'{name} lineup unavailable: {solution["error"]}')
        selected = {p['id'] for p in solution['starting_xi']}
        captain_id = solution['captain']['id']
        order = {'GK':0,'DEF':1,'MID':2,'FWD':3}
        xi = [dict(p, captain=p['id']==captain_id) for p in
              sorted(solution['starting_xi'], key=lambda p:(order[p['position']],-p['xpts']))]
        bench = sorted((p for p in solution['squad'] if p['id'] not in selected),
                       key=lambda p:(order[p['position']],-p['xpts']))
        result = {'week':week,'model':name,'risk_profile':'balanced',
            'formation':solution['formation'],'cost':solution['squad_cost'],
            'budget_remaining':round(100-solution['squad_cost'],2),
            'expected_points':solution['expected_points'],
            'risk_adjusted_objective':solution['risk_adjusted_objective'],
            'captain':solution['captain']['name'],'starting_xi':xi,'bench':bench,
            'benchmark':{'variant':'experimental_phase15','snapshot_id':snapshot_id,
                         'parameters':{'training':training,'fitted_model':fitted,
                                       'blend_weights':({NAME:0.5,'short_form_3w':0.5} if name==BLEND else None),
                                       'eligible_pool_n':len(candidates),
                                       'excluded_insufficient_history':insufficient,
                                       'production_eligibility_exclusions':production_exclusions},
                         'solver':{'status':solution['status'].upper()}}}
        prepared.append(result)
    saved = save_prediction_batch(snapshot_id,prepared,model_version=MODEL_VERSION,path=path,
                                  require_pre_deadline=True)
    return {'status':'saved','model_names':[NAME,BLEND], 'prediction_ids':[p['id'] for p in saved],
            'training':training, 'excluded_insufficient_history':insufficient}
