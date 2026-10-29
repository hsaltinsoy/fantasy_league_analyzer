"""Experimental, read-only variance/mean frontier; never used by production selection."""
import argparse
import json
from collections import Counter
from pathlib import Path

from ortools.sat.python import cp_model

from analysis.experimental_covariance import category, compare_candidates, lineup_variance
from analysis.optimizer import FORMATIONS, optimize
from analysis.prediction_tracking import DEFAULT_DB, get_prediction, get_snapshot
from analysis.predict_next_week import build_candidate_pool
from analysis.verified_fixtures_v36 import make_optimizer

SCALE = 10000
DEFAULT_MEAN_FRACTIONS = (1.0, .995, .99, .98, .97, .95)


def _and(model, first, second, name):
    both = model.NewBoolVar(name)
    model.Add(both <= first)
    model.Add(both <= second)
    model.Add(both >= first + second - 1)
    return both


def _model(players, evidence, *, budget, max_per_team, mean_floor=None, objective='variance', hint=None):
    if len({p['id'] for p in players}) != len(players):
        raise ValueError('Duplicate player IDs')
    players = sorted(players, key=lambda p:int(p['id']))
    required = {'GK':2,'DEF':5,'MID':5,'FWD':3}
    if any(Counter(p['position'] for p in players)[pos] < count for pos,count in required.items()):
        raise ValueError('Insufficient players by position')
    variance = {}
    for p in players:
        own = evidence['player_variance'].get(str(p['id']))
        value = own['variance'] if own else evidence['position_variance'].get(p['position'])
        if value is None:
            raise ValueError(f'Missing variance for player {p["id"]}; no silent substitution')
        variance[p['id']] = float(value)
    model = cp_model.CpModel()
    squad = {p['id']:model.NewBoolVar(f's_{p["id"]}') for p in players}
    start = {p['id']:model.NewBoolVar(f'x_{p["id"]}') for p in players}
    captain = {p['id']:model.NewBoolVar(f'c_{p["id"]}') for p in players}
    model.Add(sum(squad.values()) == 15)
    model.Add(sum(start.values()) == 11)
    model.Add(sum(captain.values()) == 1)
    for p in players:
        i = p['id']
        model.Add(start[i] <= squad[i])
        model.Add(captain[i] <= start[i])
        if hint is not None:
            model.AddHint(squad[i],int(i in set(hint['squad_ids'])))
            model.AddHint(start[i],int(i in set(hint['starting_xi_ids'])))
            model.AddHint(captain[i],int(i == hint['captain_id']))
    for pos,count in required.items():
        model.Add(sum(squad[p['id']] for p in players if p['position']==pos) == count)
    model.Add(sum(start[p['id']] for p in players if p['position']=='GK') == 1)
    formation_counts = [model.NewIntVar(0,5,f'{pos}_starts') for pos in ('DEF','MID','FWD')]
    for pos,count in zip(('DEF','MID','FWD'),formation_counts):
        model.Add(count == sum(start[p['id']] for p in players if p['position']==pos))
    model.AddAllowedAssignments(formation_counts, FORMATIONS)
    for team in sorted({str(p['team']) for p in players}):
        model.Add(sum(squad[p['id']] for p in players if str(p['team'])==team) <= max_per_team)
    model.Add(sum(round(float(p['price'])*100)*squad[p['id']] for p in players) <= round(budget*100))
    mean_expr = sum(round(float(p['xpts'])*SCALE)*(start[p['id']]+captain[p['id']]) for p in players)
    if mean_floor is not None:
        model.Add(mean_expr >= round(mean_floor*SCALE))
    if objective == 'mean':
        model.Maximize(mean_expr)
    elif objective == 'variance':
        terms = [round(variance[p['id']]*SCALE)*(start[p['id']]+3*captain[p['id']]) for p in players]
        for index,a in enumerate(players):
            for b in players[index+1:]:
                kind = category(a,b)
                if kind is None:
                    continue
                value = evidence['covariance'][kind]['shrunk']
                if value is None or abs(value) < 1e-10:
                    continue
                coefficient = round(2*float(value)*SCALE)
                if coefficient == 0:
                    continue
                ai, bi = a['id'], b['id']
                terms.append(coefficient*_and(model,start[ai],start[bi],f'pair_{ai}_{bi}'))
                terms.append(coefficient*_and(model,captain[ai],start[bi],f'capt_{ai}_{bi}'))
                terms.append(coefficient*_and(model,captain[bi],start[ai],f'capt_{bi}_{ai}'))
        clipped_variance = model.NewIntVar(0,1_000_000_000,'clipped_variance')
        model.Add(clipped_variance >= sum(terms))
        model.Minimize(clipped_variance)
    else:
        raise ValueError('Unknown objective')
    return model,squad,start,captain


def solve(players, evidence, *, budget=100., max_per_team=3, mean_floor=None,
          objective='variance', time_limit=12, seed=1, hint=None):
    """Optimize every legal formation jointly, with one captain and four bench players."""
    if budget <= 0 or max_per_team < 1 or time_limit <= 0:
        raise ValueError('Invalid fantasy constraints or time limit')
    model,squad,start,captain = _model(players,evidence,budget=budget,max_per_team=max_per_team,
                                       mean_floor=mean_floor,objective=objective,hint=hint)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    status = solver.Solve(model)
    label = 'optimal' if status == cp_model.OPTIMAL else 'feasible' if status == cp_model.FEASIBLE else 'not_evaluable'
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        return {'status':label,'mean_floor':mean_floor,'solver_status':solver.StatusName(status)}
    selected = [p for p in players if solver.Value(squad[p['id']])]
    xi = [p for p in players if solver.Value(start[p['id']])]
    cap = next(p for p in players if solver.Value(captain[p['id']]))
    spread = lineup_variance(xi,cap['id'],evidence)
    if spread is None:
        raise ValueError('Selected lineup lacks variance evidence')
    positions = Counter(p['position'] for p in xi)
    return {'status':label,'solver_status':solver.StatusName(status),
            'objective_bound':round(solver.BestObjectiveBound()/SCALE,4),
            'mean_floor':mean_floor,'formation':f"{positions['DEF']}-{positions['MID']}-{positions['FWD']}",
            'squad_ids':sorted(p['id'] for p in selected),
            'starting_xi_ids':sorted(p['id'] for p in xi),
            'bench_ids':sorted(p['id'] for p in selected if p['id'] not in {q['id'] for q in xi}),
            'captain_id':cap['id'],'captain_name':cap['name'],
            'squad_cost':round(sum(float(p['price']) for p in selected),2),
            'expected_points':round(sum(float(p['xpts']) for p in xi)+float(cap['xpts']),3),
            **spread}


def pareto_frontier(candidates):
    """Nondominated observed points; a time-limited solve is not a global frontier proof."""
    available = [c for c in candidates if c.get('expected_points') is not None and c.get('standard_deviation') is not None]
    unique = {}
    for candidate in available:
        key = (tuple(candidate['starting_xi_ids']),candidate['captain_id'])
        unique.setdefault(key,candidate)
    rows = list(unique.values())
    return sorted((c for c in rows if not any(
        other is not c and other['expected_points'] >= c['expected_points'] and
        other['standard_deviation'] <= c['standard_deviation'] and
        (other['expected_points'] > c['expected_points'] or other['standard_deviation'] < c['standard_deviation'])
        for other in rows)),key=lambda c:(-c['expected_points'],c['standard_deviation']))


def _snapshot_pool(snapshot, week):
    payload = snapshot['payload']
    players_by_id = {str(p['id']):p for p in payload['players']}
    records = [(players_by_id[str(h['player_id'])],h['rows']) for h in payload['histories']
               if str(h['player_id']) in players_by_id]
    if any(int(row['gameweekOrder']) >= week for _,rows in records for row in rows):
        raise ValueError('Snapshot contains future player statistics')
    fixtures = {}
    for match in payload['fixtures']:
        home,away = str(match['homeClubId']),str(match['awayClubId'])
        if home in fixtures or away in fixtures:
            raise ValueError('Duplicate fixture club in snapshot')
        fixtures[home],fixtures[away] = away,home
    pool,excluded = build_candidate_pool(week,payload['players'],records,{week:fixtures})
    adjusted = make_optimizer(records,week,.2,.15,None,0.,optimizer_func=lambda p:p)(pool)
    return adjusted,excluded


def compare_saved_gw10(*, snapshot_id='1e9f5094-9b24-42f6-a0ff-ddf201685aa8',
                       fractions=DEFAULT_MEAN_FRACTIONS,time_limit=12,path=DEFAULT_DB):
    """Use frozen GW10 inputs and the covariance evidence in its saved prediction."""
    if not fractions or any(not 0 < fraction <= 1 for fraction in fractions):
        raise ValueError('Expected-point floor fractions must be in (0, 1]')
    snapshot = get_snapshot(snapshot_id,path)
    if snapshot is None or snapshot['gameweek'] != 10:
        raise ValueError('Saved GW10 snapshot not found')
    from analysis.live_benchmark import report
    rows = [p for p in report(path=path)['predictions'] if p['snapshot_id']==snapshot_id]
    covariance_row = next((p for p in rows if p['model']=='experimental_covariance'),None)
    baseline_row = next((p for p in rows if p['model']=='short_form_3w'),None)
    if covariance_row is None or baseline_row is None:
        raise ValueError('Saved baseline and covariance predictions required')
    evidence = get_prediction(covariance_row['id'],path)['payload']['benchmark']['uncertainty']['evidence']
    pool,excluded = _snapshot_pool(snapshot,10)
    baseline_prediction = get_prediction(baseline_row['id'],path)
    pool_by_id = {p['id']:p for p in pool}
    for saved in baseline_prediction['payload']['starting_xi']:
        rebuilt = pool_by_id.get(saved['id'])
        if rebuilt is None or abs(float(rebuilt['xpts'])-float(saved['xpts'])) > .0001:
            raise ValueError('Frozen snapshot cannot reproduce saved production player scores')
    rerun = optimize(pool,risk_profile='balanced')
    if 'error' in rerun:
        raise ValueError(rerun['error'])
    reranked = compare_candidates(rerun['formation_solutions'],evidence)
    candidates = reranked['candidates']
    max_mean = solve(pool,evidence,objective='mean',time_limit=time_limit)
    if max_mean['status']=='not_evaluable':
        raise ValueError('Maximum-mean solve failed')
    floors = sorted({round(max_mean['expected_points']*fraction,3) for fraction in fractions},reverse=True)
    direct = [max_mean]
    for floor in floors:
        direct.append(solve(pool,evidence,mean_floor=floor,time_limit=time_limit,hint=max_mean))
    available = [r for r in direct if r['status']!='not_evaluable']
    rerank_rows = [{**r,'starting_xi_ids':sorted(p['id'] for p in r['starting_xi'])} for r in candidates]
    reference = baseline_prediction
    reference_ids = {p['id'] for p in reference['payload']['starting_xi']}
    names = {p['id']:p['name'] for p in pool}
    selected = reranked['selected_by_risk_aversion'].get('1.0')
    saved_covariance = get_prediction(covariance_row['id'],path)
    return {'snapshot_id':snapshot_id,'gameweek':10,
            'classification':'experimental_frozen_input_conditional_on_appearance_not_production',
            'eligible_players':len(pool),'excluded':excluded,
            'existing_candidates':{'combinations':len(candidates),
                                   'unique_xis':len({tuple(r['starting_xi_ids']) for r in rerank_rows}),
                                   'unique_squads':len({tuple(r['squad_ids']) for r in rerank_rows}),
                                   'formations':len({r['formation'] for r in candidates}),
                                   'unique_captains':len({r['captain_id'] for r in candidates}),
                                   'xi_captain_combinations':len({(tuple(r['starting_xi_ids']),r['captain_id']) for r in rerank_rows}),
                                   'selected':{k:selected.get(k) for k in ('formation','captain_name','expected_points','standard_deviation','squad_cost')} if selected else None},
            'saved_covariance_selection':{'prediction_id':saved_covariance['id'],
                                          'expected_points':saved_covariance['raw_expected_points'],
                                          'captain':saved_covariance['payload']['captain'],
                                          'formation':saved_covariance['payload']['formation'],
                                          'standard_deviation':saved_covariance['payload']['benchmark']['uncertainty']['standard_deviation']},
            'direct':{'max_mean':max_mean,'mean_floors':floors,'solutions':direct,
                      'observed_frontier':pareto_frontier(available),
                      'all_solves_proven_optimal':all(r['status']=='optimal' for r in direct)},
            'against_saved_baseline':{'captain':reference['payload']['captain'],
                                      'formation':reference['payload']['formation'],
                                      'expected_points':reference['raw_expected_points'],
                                      'standard_deviation':lineup_variance(reference['payload']['starting_xi'],
                                          next(p['id'] for p in reference['payload']['starting_xi'] if p['captain']),evidence)['standard_deviation'],
                                      'direct_player_differences':[{'mean_floor':r['mean_floor'],
                                          'only_direct':[{'id':i,'name':names[i]} for i in sorted(set(r['starting_xi_ids'])-reference_ids)],
                                          'only_baseline':[{'id':i,'name':names[i]} for i in sorted(reference_ids-set(r['starting_xi_ids']))]}
                                          for r in available]},
            'uncertainty':{'completed_match_clusters':evidence['completed_match_clusters'],
                           'covariance':{kind:{k:item.get(k) for k in ('match_clusters','pair_observations','shrunk','rough_95pct_interval')}
                                         for kind,item in evidence['covariance'].items()}},
            'limitations':['Variance is conditional on appearance, not full gameweek score variance.',
                           'Historical covariance evidence is limited to completed matches before GW10; intervals are rough.',
                           'The saved snapshot does not embed the full historical fixture archive; this experiment uses frozen covariance estimates attached to the saved GW10 prediction.',
                           'Time-limited feasible CP-SAT solutions do not prove the full Pareto frontier.',
                           'No GW10 actual points were used; lower variance does not guarantee more fantasy points.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--experimental',action='store_true',help='Explicitly run the research-only direct risk solver')
    parser.add_argument('--snapshot-id',default='1e9f5094-9b24-42f6-a0ff-ddf201685aa8')
    parser.add_argument('--time-limit',type=float,default=12)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if not args.experimental:
        parser.error('Pass --experimental to run direct risk optimization; production remains unchanged')
    result = compare_saved_gw10(snapshot_id=args.snapshot_id,time_limit=args.time_limit)
    if args.output:
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
