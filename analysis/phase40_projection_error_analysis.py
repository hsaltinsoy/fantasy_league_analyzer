"""Offline Phase 36 baseline projection audit; outcomes never choose lineups."""
import json
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path
from statistics import mean

from analysis.multiweek_backtest import MODELS, build_week
from analysis.walkforward_backtest import participation
from analysis.phase38_optimizer_audit import objective

ROOT=Path('docs')
WEEKS=range(6,12)


def summary(rows):
    if not rows:return {'n':0,'mae':None,'rmse':None,'mean_predicted':None,'mean_actual':None}
    errors=[r['predicted']-r['actual'] for r in rows]
    return {'n':len(rows),'mae':round(mean(abs(e) for e in errors),3),
            'rmse':round(sqrt(mean(e*e for e in errors)),3),
            'mean_predicted':round(mean(r['predicted'] for r in rows),3),
            'mean_actual':round(mean(r['actual'] for r in rows),3)}


def feasible_replacement(candidate,squad):
    if candidate['id'] in {p['id'] for p in squad}:return False
    for outgoing in squad:
        if outgoing['position']!=candidate['position']:continue
        trial=[p for p in squad if p['id']!=outgoing['id']]+[candidate]
        if sum(p['price'] for p in trial)<=100+1e-7 and max(Counter(str(p['team']) for p in trial).values())<=3:
            return True
    return False


def run():
    source=json.loads((ROOT/'phase28_official_histories.json').read_text(encoding='utf-8'))['rows_by_player']
    players=json.loads(Path('historical_data/players.json').read_text(encoding='utf-8'))
    records=[(p,source[str(p['id'])]) for p in players]
    phase36=json.loads((ROOT/'phase36_free_external_data.json').read_text(encoding='utf-8'))
    human=json.loads((ROOT/'phase33b_human_vs_ai.json').read_text(encoding='utf-8'))
    observations=[];weeks={};repeated=defaultdict(list);overpredicted=defaultdict(list)
    for week in WEEKS:
        pool,actual,_=build_week(records,week,MODELS['baseline_5w'])
        by_id={p['id']:p for p in pool}
        saved=phase36['historical_experiments'][str(week)]['variants']['baseline']
        xi_ids=saved['xi_ids'];bench_ids=saved['bench_ids'];captain_id=saved['captain_id']
        squad=[by_id[i] for i in xi_ids+bench_ids]
        target={str(pid):next((r for r in rows if int(r['gameweekOrder'])==week),None)
                for pid,rows in source.items()}
        wr=[]
        for p in pool:
            pid=p['id'];row=target[str(pid)]
            if row is None:continue
            past=[r for r in source[str(pid)] if int(r['gameweekOrder'])<week]
            proxy=participation(past)
            item={'week':week,'id':pid,'name':p['name'],'position':p['position'],
                'club_id':p['team'],'price_postmatch_proxy':p['price'],
                'predicted':p['xpts'],'actual':row['points'],'minutes':row['minutesPlayed'],
                'error':round(p['xpts']-row['points'],3),'participation_proxy':proxy['probability'],
                'minutes_gate_passed':proxy['probability']>=.25,
                'selected_xi':pid in xi_ids,'selected_squad':pid in xi_ids+bench_ids,
                'feasible_direct_squad_replacement':feasible_replacement(p,squad)}
            wr.append(item);observations.append(item)
            if item['error']<=-3:repeated[pid].append(item)
            if item['error']>=3:overpredicted[pid].append(item)
        weeks[str(week)]={'xi_ids':xi_ids,'bench_ids':bench_ids,'captain_id':captain_id,
            'high_actual_low_predicted':sorted((r for r in wr if r['actual']>=10 and r['predicted']<5),
                                               key=lambda r:-r['actual'])[:20],
            'high_actual_excluded_by_minutes':sorted((r for r in wr if r['actual']>=8 and not r['minutes_gate_passed']),
                                                     key=lambda r:-r['actual'])[:20],
            'high_actual_directly_affordable_unselected':sorted((r for r in wr if r['actual']>=10 and not r['selected_squad'] and r['feasible_direct_squad_replacement']),
                key=lambda r:-r['actual'])[:20],
            'high_projection_zero_minutes':sorted((r for r in wr if r['predicted']>=4 and r['minutes']==0),
                                                  key=lambda r:-r['predicted'])[:20]}
        if week==11:
            hxi=[by_id[i] for i in human['xi_ids']]
            hbench=[by_id[i] for i in human['bench_ids']]
            mxi=[by_id[i] for i in xi_ids]
            mbench=[by_id[i] for i in bench_ids]
            human_obj=objective(hxi,hbench,by_id[human['captain_id']])
            model_obj=objective(mxi,mbench,by_id[captain_id])
            shared=set(xi_ids)&set(human['xi_ids'])
            human_only=set(human['xi_ids'])-set(xi_ids)
            model_only=set(xi_ids)-set(human['xi_ids'])
            selection_pred=sum(by_id[i]['xpts'] for i in model_only)-sum(by_id[i]['xpts'] for i in human_only)
            captain_pred=by_id[captain_id]['xpts']-by_id[human['captain_id']]['xpts']
            bench_pred=.01*(sum(by_id[i]['xpts'] for i in bench_ids)-sum(by_id[i]['xpts'] for i in human['bench_ids']))
            assert abs(selection_pred+captain_pred+bench_pred-(model_obj-human_obj))<.0003
            actual_selection=sum(actual[str(i)] for i in model_only)-sum(actual[str(i)] for i in human_only)
            actual_captain=actual[str(captain_id)]-actual[str(human['captain_id'])]
            weeks['11']['human_vs_model']={'human_objective':human_obj,'model_objective':model_obj,
                'objective_gap':round(model_obj-human_obj,4),
                'selection_component':round(selection_pred,4),'captain_component':round(captain_pred,4),
                'bench_component':round(bench_pred,4),
                'actual_selection_component':actual_selection,'actual_captain_component':actual_captain,
                'shared_xi_ids':sorted(shared),'human_only_ids':sorted(human_only),'model_only_ids':sorted(model_only),
                'human_players':[next(r for r in wr if r['id']==i) for i in human['xi_ids']+human['bench_ids']],
                'model_players':[next(r for r in wr if r['id']==i) for i in xi_ids+bench_ids],
                'human_project_scoring_actual':sum(actual[str(i)] for i in human['xi_ids'])+actual[str(human['captain_id'])],
                'model_project_scoring_actual':sum(actual[str(i)] for i in xi_ids)+actual[str(captain_id)],
                'human_reported_auto_sub_points':human['players'][str(human['reported_auto_sub_id'])]['points']}
    by_position={pos:summary([r for r in observations if r['position']==pos]) for pos in ('GK','DEF','MID','FWD')}
    bands=[(0,2),(2,4),(4,6),(6,8),(8,float('inf'))]
    by_band={f'{lo}-{hi if hi!=float("inf") else "plus"}':summary([r for r in observations if lo<=r['predicted']<hi]) for lo,hi in bands}
    by_participation={label:summary([r for r in observations if fn(r)]) for label,fn in
        [('zero',lambda r:r['minutes']==0),('under60',lambda r:0<r['minutes']<60),('60plus',lambda r:r['minutes']>=60)]}
    repeated_rows=[{'id':pid,'name':rows[0]['name'],'weeks':[r['week'] for r in rows],
                    'total_underprediction':round(-sum(r['error'] for r in rows),3)}
                   for pid,rows in repeated.items() if len(rows)>=2]
    repeated_rows.sort(key=lambda r:(-len(r['weeks']),-r['total_underprediction']))
    repeated_over=[{'id':pid,'name':rows[0]['name'],'weeks':[r['week'] for r in rows],
                    'zero_minute_weeks':[r['week'] for r in rows if r['minutes']==0],
                    'total_overprediction':round(sum(r['error'] for r in rows),3)}
                   for pid,rows in overpredicted.items() if len(rows)>=2]
    repeated_over.sort(key=lambda r:(-len(r['weeks']),-r['total_overprediction']))
    result={'classification':'approximate_retrospective_phase36_baseline_error_audit',
        'source_retrieved_at':json.loads((ROOT/'phase28_official_histories.json').read_text(encoding='utf-8'))['retrieved_at'],
        'n_player_weeks':len(observations),'overall':summary(observations),
        'by_position':by_position,'by_predicted_band':by_band,'by_actual_participation':by_participation,
        'high_actual_10plus':summary([r for r in observations if r['actual']>=10]),
        'repeated_underpredicted':repeated_rows,'repeated_overpredicted':repeated_over,'weeks':weeks,
        'warnings':['Phase 36 pool differs from Phase 32 GW11 pool',
            'Historical club and price proxies are not verified deadline snapshots',
            'Official rows were retrieved after evaluated weeks; publication timing unverified',
            'Actual outcomes were read only for evaluation and reporting, never for lineup selection',
            'Budget-feasible direct replacement is a one-player test, not proof of globally feasible optimal XI']}
    (ROOT/'phase40_projection_error_analysis.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    report(result)
    return result


def report(d):
    h=d['weeks']['11']['human_vs_model']
    lines=['# Phase 40 — player projection errors and missed high scorers','',
        '**Classification:** approximate retrospective audit of the exact Phase 36 baseline 5W candidate pool and legacy optimizer policy. Phase 32 is a different GW11 experiment. No lineup is chosen using actual results.','',
        '## GW11 human versus optimizer projection accounting','',
        f'Human predicted objective **{h["human_objective"]:.4f}**, Phase 36 optimizer **{h["model_objective"]:.4f}**. Optimizer advantage **{h["objective_gap"]:+.4f}** = XI selection **{h["selection_component"]:+.4f}** + captain **{h["captain_component"]:+.4f}** + 1% bench tie-break **{h["bench_component"]:+.4f}**. This is the optimizer’s own prediction scale; it does not include a substitution expectation.','',
        f'On official outcomes the human XI + captain scored **{h["human_project_scoring_actual"]}**, the Phase 36 model XI + captain **{h["model_project_scoring_actual"]}**. Model minus human is **{h["actual_selection_component"]:+.0f}** from XI choices and **{h["actual_captain_component"]:+.0f}** from captain choice, exactly **{h["model_project_scoring_actual"]-h["human_project_scoring_actual"]:+.0f}**. The human’s reported Murillo substitution adds **{h["human_reported_auto_sub_points"]}** separately, reaching 105; no equivalent model substitution was applied. These realized outcomes are evaluation only.','',
        '| Squad | Role | Player | Predicted xPts | Actual GW11 | Minutes | Proxy | Error |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for squad,key,xi_ids,cap in [('human','human_players',set(d['weeks']['11']['human_vs_model']['shared_xi_ids']+d['weeks']['11']['human_vs_model']['human_only_ids']),176),
                               ('optimizer','model_players',set(d['weeks']['11']['xi_ids']),d['weeks']['11']['captain_id'])]:
        for p in h[key]:
            role='Captain' if p['id']==cap else 'XI' if p['id'] in xi_ids else 'Bench'
            lines.append(f'| {squad} | {role} | {p["name"]} ({p["id"]}) | {p["predicted"]:.3f} | {p["actual"]} | {p["minutes"]} | {p["participation_proxy"]:.3f} | {p["error"]:+.3f} |')
    lines+=['','## GW6–11 projection quality','',
        f'{d["n_player_weeks"]} player-weeks: MAE **{d["overall"]["mae"]:.3f}**, RMSE **{d["overall"]["rmse"]:.3f}**. Calibration below is mean predicted versus mean actual by projection band, not a calibrated probabilistic forecast.','',
        '| Position | N | MAE | RMSE | Mean predicted / actual |','| --- | ---: | ---: | ---: | ---: |']
    for name,m in d['by_position'].items():lines.append(f'| {name} | {m["n"]} | {m["mae"]:.3f} | {m["rmse"]:.3f} | {m["mean_predicted"]:.3f} / {m["mean_actual"]:.3f} |')
    lines+=['','| Predicted xPts band | N | MAE | RMSE | Mean predicted / actual |','| --- | ---: | ---: | ---: | ---: |']
    for name,m in d['by_predicted_band'].items():
        if m['n']:lines.append(f'| {name} | {m["n"]} | {m["mae"]:.3f} | {m["rmse"]:.3f} | {m["mean_predicted"]:.3f} / {m["mean_actual"]:.3f} |')
    lines+=['','| Actual minutes | N | MAE | Mean predicted / actual |','| --- | ---: | ---: | ---: |']
    for name,m in d['by_actual_participation'].items():lines.append(f'| {name} | {m["n"]} | {m["mae"]:.3f} | {m["mean_predicted"]:.3f} / {m["mean_actual"]:.3f} |')
    top=d['high_actual_10plus']
    lines+=['',f'High-upside realized scorers (10+ actual): {top["n"]} player-weeks, mean predicted {top["mean_predicted"]:.3f} versus actual {top["mean_actual"]:.3f}, MAE {top["mae"]:.3f}. This selection by **actual** score is descriptive and cannot be used to choose pre-deadline players.','',
        '## Missed scorers and participation errors','']
    for week,row in d['weeks'].items():
        lines += [f'**GW{week}:** high actual (10+) with projection under 5: {len(row["high_actual_low_predicted"])}; high actual (8+) below 0.25 minutes gate: {len(row["high_actual_excluded_by_minutes"])}; high actual (10+) not in the 15 but feasible by one same-position squad replacement: {len(row["high_actual_directly_affordable_unselected"])}; projected 4+ with zero minutes: {len(row["high_projection_zero_minutes"])}.', '']
    lines+=['Repeated underprediction (at least two weeks with actual exceeding prediction by 3+): '+', '.join(f'{r["name"]} ({r["id"]}) GW{r["weeks"]}' for r in d['repeated_underpredicted'][:12])+'. Full player-level lists and minutes are in JSON. Repeated misses warrant study, but these thresholds and labels were applied after outcomes and do not prove predictability.','',
        'Repeated overprediction (at least two weeks with prediction exceeding actual by 3+): '+', '.join(f'{r["name"]} ({r["id"]}) GW{r["weeks"]}, zero-minute GW{r["zero_minute_weeks"]}' for r in d['repeated_overpredicted'][:12])+'. The JSON retains full lists. These outcome-defined groups are diagnostic, not causal.','',
        '## Missing information and controlled next experiments','',
        '| Priority | Hypothesis | Required free pre-deadline data | Evaluation / leakage control | Success criterion |',
        '| ---: | --- | --- | --- | --- |',
        '| 1 | Zero-minute and short-appearance errors depress selected-XI scores | Timestamped official status, recent starts/minutes, legally accessible club injury/squad notices | Prospective snapshots; compare zero-minute rate and player MAE on identical eligible pools | Lower zero-minute XI rate and MAE across multiple weeks without reducing realized XI score |',
        '| 2 | Team attack and opponent defense explain repeated high-upside misses | Permitted, timestamped team xG/goals/shots and opponent conceded data | Event and publication time before deadline; paired model comparison on same players | Lower high-upside MAE and improved multiple-week XI scores |',
        '| 3 | Captain potential differs from raw form | Save captain bonus alternatives and prior starts/minutes | Pre-deadline captain rankings; evaluate captain actuals after finalization | Consistent multiweek gain, not one exceptional week |','',
        'Existing free TFF fantasy histories contain points, starts and minutes; deadline-time status revisions are not archived. Football-Data offers team-level CSV with [restrictive fair-use terms](https://football-data.co.uk/contact.php), not player-level xG/xA. No unverified provider was used as if it supplied historical player availability.','',
        '## Limits and verification','',
        'All rows use history strictly before each target GW for xPts and participation proxies. The local player archive supplies current club/position labels and positive postmatch price proxies; exact historical prices, availability and club assignments are unverified. The GW11 comparison uses Phase 36 only and the original seven-formation legacy policy. Model weights, optimizer, frozen snapshots and earlier reports were not changed. Focused regression tests cover objective decomposition and outcome-independent feasibility.','']
    (ROOT/'phase40_projection_error_analysis.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    r=run();print(r['overall'],r['weeks']['11']['human_vs_model']['objective_gap'])
