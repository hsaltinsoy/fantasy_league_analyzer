"""Read-only optimizer audit using reconstructed Phase 36 pools and exact small search."""
import itertools
import json
from collections import Counter
from pathlib import Path

from analysis.multiweek_backtest import MODELS, build_week
from analysis.optimizer import FORMATIONS, optimize

HUMAN_XI=(130,120,94,27,212,176,281,877,507,148,593)
HUMAN_BENCH=(216,277,597,4)
HUMAN_CAPTAIN=176
OUT=Path('docs/phase38_optimizer_audit.json')


def objective(xi,bench,captain,risk_penalty=0):
    return round(sum(p['xpts'] for p in xi)+captain['xpts']+
                 .01*sum(p['xpts'] for p in bench)-risk_penalty,4)


def validate(squad,xi,captain,budget=100):
    sc=Counter(p['position'] for p in squad)
    xc=Counter(p['position'] for p in xi)
    clubs=Counter(str(p['team']) for p in squad)
    return {'unique_ids':len({p['id'] for p in squad})==15,
        'squad_count':len(squad)==15,'xi_count':len(xi)==11,
        'squad_positions':dict(sc),'positions_legal':all(sc[k]==v for k,v in
            {'GK':2,'DEF':5,'MID':5,'FWD':3}.items()),
        'xi_formation':f'{xc["DEF"]}-{xc["MID"]}-{xc["FWD"]}',
        'formation_legal':xc['GK']==1 and (xc['DEF'],xc['MID'],xc['FWD']) in FORMATIONS,
        'club_limit':max(clubs.values())<=3,'cost':sum(p['price'] for p in squad),
        'budget_legal':sum(p['price'] for p in squad)<=budget+1e-7,
        'xi_in_squad':{p['id'] for p in xi}<={p['id'] for p in squad},
        'captain_in_xi':captain['id'] in {p['id'] for p in xi}}


def evaluate_week(week,records):
    pool,_,_=build_week(records,week,MODELS['baseline_5w'])
    pool=[{k:v for k,v in p.items() if k!='actual_points'} for p in pool]
    result=optimize(pool,formation_policy='legacy_pre39_v1')
    if 'error' in result:raise RuntimeError(result['error'])
    selected={p['id'] for p in result['starting_xi']}
    bench=[p for p in result['squad'] if p['id'] not in selected]
    checks=validate(result['squad'],result['starting_xi'],result['captain'])
    assert all(v for k,v in checks.items() if k not in ('squad_positions','xi_formation','cost'))
    assert abs(objective(result['starting_xi'],bench,result['captain'])-result['risk_adjusted_objective'])<.0002
    # Independent arithmetic and one-player feasible neighborhood, without target outcomes.
    current=result['risk_adjusted_objective']
    candidates=[]
    outside=[p for p in pool if p['id'] not in {q['id'] for q in result['squad']}]
    for leaving in result['starting_xi']:
        for entering in outside:
            if entering['position']!=leaving['position']:continue
            trial_squad=[p for p in result['squad'] if p['id']!=leaving['id']]+[entering]
            trial_xi=[p for p in result['starting_xi'] if p['id']!=leaving['id']]+[entering]
            trial_cap=max(trial_xi,key=lambda p:p['xpts'])
            c=validate(trial_squad,trial_xi,trial_cap)
            if not all(c[k] for k in ('unique_ids','positions_legal','formation_legal','club_limit','budget_legal')):continue
            trial_bench=[p for p in trial_squad if p['id'] not in {q['id'] for q in trial_xi}]
            candidates.append((objective(trial_xi,trial_bench,trial_cap),leaving['id'],entering['id']))
    best_neighbor=max(candidates,default=None)
    sensitivity=None
    if week==8 and best_neighbor and current-best_neighbor[0]<.1:
        perturbed=[{**p,'xpts':round(p['xpts']+.1,3)} if p['id']==best_neighbor[2] else p for p in pool]
        alternate=optimize(perturbed,formation_policy='legacy_pre39_v1')
        if 'error' in alternate:raise RuntimeError(alternate['error'])
        sensitivity={'perturbed_player_id':best_neighbor[2],'delta_xpts':.1,
            'xi_overlap':len(selected&{p['id'] for p in alternate['starting_xi']}),
            'formation':alternate['formation'],'captain_id':alternate['captain']['id'],
            'bench_overlap':len({p['id'] for p in bench}&
                {p['id'] for p in alternate['squad'] if p['id'] not in {q['id'] for q in alternate['starting_xi']}})}
    human=None
    if week==11:
        by_id={p['id']:p for p in pool}
        ids=set(HUMAN_XI+HUMAN_BENCH)
        missing=sorted(ids-set(by_id))
        if not missing:
            hs=[by_id[i] for i in HUMAN_XI+HUMAN_BENCH]
            hx=[by_id[i] for i in HUMAN_XI]
            hc=by_id[HUMAN_CAPTAIN]
            human_checks=validate(hs,hx,hc)
            human={'checks':human_checks,'predicted_objective':objective(hx,[by_id[i] for i in HUMAN_BENCH],hc),
                   'optimizer_objective':current,'objective_gap':round(current-objective(hx,[by_id[i] for i in HUMAN_BENCH],hc),4),
                   'human_xi_ids':list(HUMAN_XI),'optimizer_xi_ids':[p['id'] for p in result['starting_xi']],
                   'human_captain_xpts':hc['xpts'],'optimizer_captain_xpts':result['captain']['xpts'],
                   'human_only':[{'id':i,'name':by_id[i]['name'],'xpts':by_id[i]['xpts']} for i in set(HUMAN_XI)-selected],
                   'optimizer_only':[{'id':i,'name':by_id[i]['name'],'xpts':by_id[i]['xpts']} for i in selected-set(HUMAN_XI)]}
        else:human={'missing_ids':missing}
    return {'week':week,'candidate_count':len(pool),'status':result['status'],
        'all_formations_proven_optimal':result['all_formations_proven_optimal'],
        'formation_statuses':[{k:v for k,v in c.items() if k in ('formation','status','risk_adjusted_objective')} for c in result['formation_comparison']],
        'checks':checks,'objective':current,'fantasy_xpts':result['expected_fantasy_points'],
        'formation':result['formation'],'captain_id':result['captain']['id'],
        'captain_is_highest_xpts_in_xi':result['captain']['xpts']==max(p['xpts'] for p in result['starting_xi']),
        'xi_ids':[p['id'] for p in result['starting_xi']],
        'bench_ids':[p['id'] for p in bench],
        'feasible_one_swap_count':len(candidates),'best_one_swap_objective':best_neighbor,
        'best_one_swap_gap':round(current-best_neighbor[0],4) if best_neighbor is not None else None,
        'best_one_swap_ids':list(best_neighbor[1:]) if best_neighbor else None,
        'sensitivity':sensitivity,
        'human':human}


def run():
    fetched=json.loads(Path('docs/phase28_official_histories.json').read_text(encoding='utf-8'))
    players=json.loads(Path('historical_data/players.json').read_text(encoding='utf-8'))
    records=[(p,fetched['rows_by_player'][str(p['id'])]) for p in players]
    weeks={str(w):evaluate_week(w,records) for w in (6,8,11)}
    result={'classification':'approximate_retrospective_optimizer_audit',
        'reconstructed_weeks':weeks,
        'constraints':{'budget':100,'squad_positions':{'GK':2,'DEF':5,'MID':5,'FWD':3},
            'xi_size':11,'captain_count':1,'max_per_club':3,
            'formations':['-'.join(map(str,f)) for f in FORMATIONS],
            'declared_objective':'XI xPts + risk-adjusted captain bonus + 0.01 bench xPts - opposing-pair risk penalty'},
        'warnings':['Phase 36 historical pool uses current archived club identity and postmatch price proxies',
            'GW11 human comparison uses Phase 36 baseline pool, not Phase 32 frozen GW11 input bundle',
            'One-swap neighborhood is not a global optimality proof',
            'Only CP-SAT OPTIMAL status for every legal formation proves its modeled global objective']}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    report(result)
    return result


def report(d):
    lines=['# Phase 38 — fantasy squad optimizer decision quality','',
        '**Scope:** read-only audit of the existing CP-SAT optimizer using historical predicted points only. No GW target results enter selection.','',
        '## Declared constraints and objective','',
        'The model selects exactly 15 players (2 GK, 5 DEF, 5 MID, 3 FWD), 11 starters, one starter captain, at most three players per club and cost at most 100. It solves seven legal formations separately. The objective is XI xPts plus risk-adjusted captain-bonus xPts plus 1% of bench xPts, less opposing attacker/defender risk penalties. This is **not** simply maximum raw fantasy xPts. The solver returns `optimal` or a time-limited `feasible` status per formation; only all-optimal statuses prove global optimality under the encoded objective.','',
        '## Reconstructed historical checks','',
        '| GW | Pool | Formation | Captain ID | Objective | Fantasy xPts | All formations optimal | Feasible one-swaps | Best one-swap gap |',
        '| ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: |']
    for week,row in d['reconstructed_weeks'].items():
        lines.append(f'| {week} | {row["candidate_count"]} | {row["formation"]} | {row["captain_id"]} | {row["objective"]:.4f} | {row["fantasy_xpts"]:.2f} | {row["all_formations_proven_optimal"]} | {row["feasible_one_swap_count"]} | {row["best_one_swap_gap"]} |')
    lines+=['','Every returned lineup passed independent arithmetic checks for squad size, position counts, formation, club limit, budget, starter membership and captain membership. The recomputed objective matched solver output. A separate feasible one-player starter swap scan found no better modeled score where the reported gap is nonnegative. This neighborhood scan is not a global proof and ignores multi-player swaps. Per-formation solver statuses are in JSON.','',
        '## Captain consistency','',
        'For the reconstructed pools, the captain is checked against the maximum raw XI xPts; results are in JSON. In production Phase 32, `make_optimizer` applies a risk-adjusted `captain_bonus_xpts`, so the mathematically correct captain may differ from the highest raw xPts. The CP-SAT objective chooses captain jointly with the XI and bench. The TFF scoring rule doubles captain fantasy points; risk adjustment is a decision preference, not a different official scoring multiplier.','',
        '## Human GW11 squad under reconstructed constraints','']
    h=d['reconstructed_weeks']['11']['human']
    if 'missing_ids' in h:
        lines.append(f'Human squad missing from this reconstructed pool: {h["missing_ids"]}. Objective comparison blocked.')
    else:
        c=h['checks']
        lines += [f'Human squad check: 15 players (count valid: {c["squad_count"]}), cost {c["cost"]:.1f}, formation {c["xi_formation"]}, club limit {c["club_limit"]}, budget legal {c["budget_legal"]}. Predicted objective **{h["predicted_objective"]:.4f}** versus optimizer **{h["optimizer_objective"]:.4f}**; gap **{h["objective_gap"]:+.4f}** under the same Phase 36 reconstructed pool. Human captain xPts {h["human_captain_xpts"]:.3f}; optimizer captain xPts {h["optimizer_captain_xpts"]:.3f}.','',
            'Human-only XI projections: '+', '.join(f'{p["name"]} ({p["id"]}) {p["xpts"]:.3f}' for p in h['human_only'])+'.','',
            'Optimizer-only XI projections: '+', '.join(f'{p["name"]} ({p["id"]}) {p["xpts"]:.3f}' for p in h['optimizer_only'])+'.','']
    lines+=['## Sensitivity and limitations','',
        'The objective gives bench quality only 1% weight, so near-tied XI choices can change after small xPts perturbations. Captain is selected jointly and can change when captain-bonus terms are close. This audit reports objective margins to feasible one-swaps; a complete perturbation sweep was not run. Do not infer realized superiority from a higher predicted objective.','']
    sensitivity=d['reconstructed_weeks']['8']['sensitivity']
    if sensitivity:
        lines += [f'GW8 local perturbation: raising player {sensitivity["perturbed_player_id"]} by {sensitivity["delta_xpts"]:.1f} xPts led to {sensitivity["xi_overlap"]}/11 XI overlap, {sensitivity["bench_overlap"]}/4 bench overlap, formation {sensitivity["formation"]}, captain {sensitivity["captain_id"]}. This is a sensitivity probe, not evidence of a better forecast.','']
    lines += [
        'Historical prices and clubs are reconstructed from postmatch/current metadata, and GW11 human feasibility here is not proof of exact deadline feasibility. Phase 32 and 33B remain separate: the human 105 actual points and model actual points were never fed to the optimizer. The optimizer omits **5-2-3**, which [current official TFF help](https://tfffantezilig.com/yardim?tab=sss) lists as legal. This is a confirmed rules-coverage gap. Thus `all_formations_proven_optimal` proves optimality only among the seven encoded formations, not all eight official formations. This audit did not alter production rules or retrospective lineups.','',
        '## Priorities','',
        '1. Verify formation coverage against current official TFF rules and add regression coverage for any confirmed omission.',
        '2. Persist per-formation optimality status and objective gap with every future lineup; a `feasible` time-limited result is not a proof.',
        '3. Audit captain-bonus alternatives and near-tied lineups on genuinely timestamped future inputs.',
        '4. Capture historical price, club and availability metadata before deadlines to make retrospective feasibility meaningful.','',
        'Focused tests cover constraint arithmetic and objective/alternative comparisons. Frozen snapshots, saved predictions and production weights were not modified.','']
    Path('docs/phase38_optimizer_audit.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    print({w:(r['objective'],r['status']) for w,r in run()['reconstructed_weeks'].items()})
