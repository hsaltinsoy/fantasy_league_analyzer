"""Exploratory GW12 optimizer diagnostics from one immutable snapshot."""
import argparse
import json
from collections import Counter
from datetime import datetime

from analysis.availability import evaluate as availability
from analysis.capture_integrity import validate_inputs
from analysis.football_data_live import make_adjuster_from_matches
from analysis.multisource_experimental import rest_days_adjustment
from analysis.optimizer import optimize
from analysis.predict_next_week import build_candidate_pool
from analysis.verified_fixtures_v36 import make_optimizer
from analysis.walkforward_backtest import participation
from analysis.walkforward_v27 import fixture_multipliers
from analysis.production_scoring import lineup_player_points
from analysis.live_benchmark import _fixture_lookup
from analysis.prediction_tracking import get_snapshot, _postgres, DEFAULT_DB

SNAPSHOT = 'ceddd5ae-a154-411b-9581-31a484c87f5f'
INPUT_HASH = '8029bd1b4525fd5fe5fb9835bfea1ea8e7a274289604afc3f188dfa62b87aa1d'
BATCH = 'd6d19fbe3a479c11691d140409eba665d2cee53ab6dd88b6ecf8eff05f1ed4fe'


def _summary(solution):
    if 'error' in solution:
        return {'error': solution['error']}
    ids = {p['id'] for p in solution['starting_xi']}
    return {'formation': solution['formation'], 'captain': solution['captain']['name'],
            'cost': solution['squad_cost'], 'status': solution['status'],
            'all_formations_proven_optimal': solution['all_formations_proven_optimal'],
            'objective': solution['risk_adjusted_objective'],
            'fantasy_points': solution['expected_fantasy_points'],
            'xi': [{'id': p['id'], 'name': p['name']} for p in solution['starting_xi']],
            'bench': [{'id': p['id'], 'name': p['name']} for p in solution['squad'] if p['id'] not in ids]}


def run(snapshot_id=SNAPSHOT, *, time_limit=4):
    snapshot = get_snapshot(snapshot_id)
    if snapshot is None:
        raise ValueError('Frozen snapshot missing')
    payload = snapshot['payload']
    week = snapshot['gameweek']
    if validate_inputs(week, payload['players'], payload['fixtures'], payload['histories']) != INPUT_HASH:
        raise ValueError('Frozen input hash mismatch')
    lookup = {week: _fixture_lookup({'matches': payload['fixtures']})}
    history = {str(row['player_id']): row['rows'] for row in payload['histories']}
    records = [(p, history[str(p['id'])]) for p in payload['players']]
    strengths = fixture_multipliers(records, week)
    base_pool, exclusions = build_candidate_pool(week, payload['players'], records, lookup,
                                                  availability_policy='legacy_pre31a')
    minutes_rows = []
    for p in payload['players']:
        past = [r for r in history[str(p['id'])] if int(r['gameweekOrder']) < week]
        if not past or str(p.get('club_id') or p.get('team')) not in lookup[week]:
            continue
        proxy = participation(past)
        if proxy['probability'] >= .25:
            continue
        club = str(p.get('club_id') or p.get('team'))
        opponent = lookup[week][club]
        state = availability(p, round_number=week)
        projection = None
        try:
            projection = lineup_player_points(p, past, 'short_form_3w',
                1 + .5 * (strengths.get((opponent, p['position']), 1.) - 1), state['factor'])
        except (ValueError, KeyError):
            pass
        last4 = [r.get('minutesPlayed') for r in past[-4:]]
        minutes_rows.append({'id': p['id'], 'name': p['name'], 'position': p['position'],
            'price': p.get('price'), 'last_four_minutes': last4,
            'historical_minutes': [r.get('minutesPlayed') for r in past],
            'recent_appearances': sum((m or 0) > 0 for m in last4),
            'probability': proxy['probability'], 'threshold': .25,
            'short_form_projection_if_admitted': projection,
            'availability': state['status']})
    pg = _postgres(DEFAULT_DB)
    saved = [pg.get_prediction(pid) for pid in pg.prediction_ids(snapshot_id)]
    saved = {r['model']: r['payload'] for r in saved
             if (r['payload'].get('benchmark') or {}).get('batch_id') == BATCH}
    if len(saved) != 6:
        raise ValueError('Incomplete saved six-model batch')
    archive = {'weeks': {str(week): {'matches': payload['fixtures']}}}
    cutoff = datetime.fromisoformat(snapshot['captured_at'].replace('Z', '+00:00'))
    matches = payload['feature_evidence']['football_data_matches']
    by_model = {}
    pool_projections = {}
    budget_sensitivity = {}
    for name in sorted(saved):
        model = name if name in ('baseline_5w', 'short_form_3w', 'stable_8w') else 'short_form_3w'
        pool, excluded = build_candidate_pool(week, payload['players'], records, lookup, model,
                                              availability_policy='legacy_pre31a')
        if name in ('uniform_xg', 'position_aware_xg'):
            adjust, _ = make_adjuster_from_matches(matches, archive, week, cutoff, name, .4)
            pool = adjust(pool)
        elif name == 'rest_days_control':
            pool = [rest_days_adjustment(p, {}, None, 0) for p in pool]
        prepared = []
        make_optimizer(records, week, .2, .15, {}, 0,
                       optimizer_func=lambda rows: prepared.extend(rows) or {})(pool)
        pool_projections[name] = {str(p['id']): p['xpts'] for p in prepared}
        osimhen = next((p for p in prepared if p['id'] == 507), None)
        if osimhen is None:
            by_model[name] = {'eligible': False, 'exclusions': excluded}
            continue
        forwards = sorted((p for p in prepared if p['position'] == 'FWD'),
                          key=lambda p: -p['xpts'])
        original = saved[name]
        forced_squad = optimize(prepared, force_squad_ids=(507,), time_limit=time_limit)
        forced_start = optimize(prepared, force_start_ids=(507,), time_limit=time_limit)
        original_squad = {p['id'] for p in original['starting_xi'] + original['bench']}
        def changes(solution):
            if 'error' in solution:
                return None
            selected = {p['id'] for p in solution['squad']}
            names = {p['id']: p['name'] for p in prepared}
            return {'entered': [names[i] for i in sorted(selected-original_squad)],
                    'left': [names[i] for i in sorted(original_squad-selected)],
                    'objective_delta_vs_saved': round(solution['risk_adjusted_objective'] -
                                                     original['risk_adjusted_objective'], 4)}
        by_model[name] = {'eligible': True, 'osimhen': {k: osimhen.get(k) for k in
            ('id', 'name', 'position', 'price', 'xpts', 'captain_bonus_xpts', 'participation_probability')},
            'forward_rank': next(i for i,p in enumerate(forwards,1) if p['id']==507),
            'selected_forwards': [{k:p[k] for k in ('id','name','xpts','price')}
                for p in original['starting_xi'] if p['position']=='FWD'],
            'saved': {'formation': original['formation'], 'captain': original['captain'],
                'cost': original['cost'], 'objective': original['risk_adjusted_objective'],
                'fantasy_points': original['expected_fantasy_points']},
            'forced_squad': _summary(forced_squad), 'forced_squad_changes': changes(forced_squad),
            'forced_start': _summary(forced_start), 'forced_start_changes': changes(forced_start)}
        budget_sensitivity[name] = {}
        for budget in (85, 90, 95):
            if budget < saved[name]['cost']:
                check = optimize(prepared, budget=budget, time_limit=time_limit)
                budget_sensitivity[name][str(budget)] = {
                    'status': check.get('status', 'infeasible'),
                    'objective': check.get('risk_adjusted_objective'),
                    'cost': check.get('squad_cost')}
            else:
                budget_sensitivity[name][str(budget)] = {
                    'status': 'no_lower_budget_needed',
                    'objective': saved[name]['risk_adjusted_objective'],
                    'cost': saved[name]['cost']}
    threshold_sensitivity = {}
    for threshold in (.1, .25, .4):
        candidate, counts = build_candidate_pool(week, payload['players'], records, lookup,
                                                  min_probability=threshold,
                                                  availability_policy='legacy_pre31a')
        prepared = []
        make_optimizer(records, week, .2, .15, {}, 0,
                       optimizer_func=lambda rows: prepared.extend(rows) or {})(candidate)
        solution = optimize(prepared, time_limit=time_limit)
        threshold_sensitivity[str(threshold)] = {'eligible': len(candidate),
            'excluded': counts, 'solution': _summary(solution)}
    return {'classification':'exploratory_frozen_gw12', 'snapshot_id': snapshot_id,
            'input_hash': INPUT_HASH, 'batch_id': BATCH, 'source_capture': snapshot['captured_at'],
            'exclusions': exclusions, 'minutes_excluded_count': len(minutes_rows),
            'minutes_excluded': minutes_rows,
            'threshold_sensitivity': threshold_sensitivity,
            'budget_sensitivity': budget_sensitivity,
            'pool_projections': pool_projections,
            'models': by_model}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='docs/phase25_diagnostics.json')
    parser.add_argument('--time-limit', type=float, default=4)
    args = parser.parse_args()
    result = run(time_limit=args.time_limit)
    with open(args.output, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps({'output': args.output, 'models': list(result['models']),
                      'minutes_excluded': result['minutes_excluded_count']}, ensure_ascii=False))
