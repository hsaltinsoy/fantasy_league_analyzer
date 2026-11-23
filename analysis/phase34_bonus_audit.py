"""Offline, leakage-checked audit of official bonus and an experimental decomposition."""
import json
from collections import defaultdict
from math import sqrt
from pathlib import Path
from statistics import mean

from analysis.multiweek_backtest import MODELS, build_week, project
from analysis.optimizer import optimize

ROOT = Path('docs')
HISTORY = ROOT/'phase28_official_histories.json'
HUMAN = ROOT/'phase33b_human_vs_ai.json'
SIX = ROOT/'phase32_gw11_walkforward.json'
MODELS_TESTED = ('baseline_5w','short_form_3w','stable_8w')
WEEKS = (6,7,8,9,10,11)


def bonus_value(row):
    value = row.get('bonus')
    if value is None:
        raise ValueError('Missing official bonus field')
    return float(value)


def experimental(p, past, config):
    """Replace the embedded bonus component; never add it to total-point projection."""
    base_rows = [{**r, 'points': float(r['points'])-bonus_value(r)} for r in past]
    base = project(p, base_rows, config)
    recent = past[-5:]
    bonus = mean(bonus_value(r) for r in recent)
    availability = min(1, max(.1, mean(float(r.get('minutesPlayed') or 0) for r in recent)/85))
    return round(max(.1, base + bonus*availability), 3)


def score_solution(solution, actual):
    xi = solution['starting_xi']
    captain = solution['captain']['id']
    if any(str(p['id']) not in actual for p in xi):
        return None
    return sum(actual[str(p['id'])] for p in xi)+actual[str(captain)]


def run():
    fetched = json.loads(HISTORY.read_text(encoding='utf-8'))
    all_rows = fetched['rows_by_player']
    players = json.loads(Path('historical_data/players.json').read_text(encoding='utf-8'))
    rows = [r for values in all_rows.values() for r in values if int(r['gameweekOrder']) <= 11]
    coverage = {'rows': len(rows), 'with_points': sum(r.get('points') is not None for r in rows),
                'with_bonus': sum(r.get('bonus') is not None for r in rows),
                'nonzero_bonus': sum((r.get('bonus') or 0)>0 for r in rows),
                'bonus_by_week': {str(w): sum(float(r.get('bonus') or 0) for r in rows if int(r['gameweekOrder'])==w)
                                  for w in range(1,12)}}
    breakdown = [r for r in rows if isinstance(r.get('breakdown'), list)]
    mismatches = []
    for r in breakdown:
        events = r['breakdown']
        if all(e.get('subtotal') is not None for e in events):
            total = sum(float(e['subtotal']) for e in events)
            if abs(total-float(r['points']))>.001:
                mismatches.append({'week':r['gameweekOrder'],'points':r['points'],'breakdown_total':total})
    coverage['breakdown_rows'] = len(breakdown)
    coverage['breakdown_point_mismatches'] = len(mismatches)
    human = json.loads(HUMAN.read_text(encoding='utf-8'))
    six = json.loads(SIX.read_text(encoding='utf-8'))['models']
    gw11 = {str(pid): next((r for r in values if int(r['gameweekOrder'])==11), None)
            for pid,values in all_rows.items()}
    def split(ids, captain):
        detail = [{'id': i,'points': gw11[str(i)]['points'],'bonus': gw11[str(i)]['bonus'],
                   'base': gw11[str(i)]['points']-gw11[str(i)]['bonus'] } for i in ids]
        return {'players':detail,'xi_bonus':sum(p['bonus'] for p in detail),
                'captain_extra_bonus':gw11[str(captain)]['bonus'],
                'total_bonus_with_captain':sum(p['bonus'] for p in detail)+gw11[str(captain)]['bonus']}
    contributions = {'human':split(human['xi_ids'],human['captain_id']),
                     'human_murillo_bonus':gw11[str(human['reported_auto_sub_id'])]['bonus']}
    for name,m in six.items():
        contributions[name] = split([p['id'] for p in m['starting_xi']],m['captain_id'])
    high = [{**p,'bonus':gw11[str(p['id'])]['bonus'],
             'base':p['points']-gw11[str(p['id'])]['bonus']}
            for p in json.loads(SIX.read_text(encoding='utf-8'))['high_actual_not_in_any_xi']]
    records = [(p, all_rows[str(p['id'])]) for p in players if str(p['id']) in all_rows]
    metrics = defaultdict(dict)
    squad = defaultdict(dict)
    for week in WEEKS:
        for name in MODELS_TESTED:
            config = MODELS[name]
            pool, actual, _ = build_week(records,week,config)
            pool = [{k:v for k,v in item.items() if k != 'actual_points'} for item in pool]
            exp_pool = []
            errors = {'baseline':[],'experimental':[]}
            for item in pool:
                past = [r for r in all_rows[str(item['id'])] if int(r['gameweekOrder'])<week]
                adjusted = experimental(next(p for p in players if p['id']==item['id']),past,config)
                exp_pool.append({**item,'xpts':adjusted})
                if str(item['id']) in actual:
                    errors['baseline'].append(item['xpts']-actual[str(item['id'])])
                    errors['experimental'].append(adjusted-actual[str(item['id'])])
            metrics[str(week)][name] = {variant:{'n':len(values),
                    'mae':round(mean(abs(v) for v in values),3),
                    'rmse':round(sqrt(mean(v*v for v in values)),3)}
                    for variant,values in errors.items()}
            if name == 'baseline_5w':
                base_solution = optimize(pool)
                exp_solution = optimize(exp_pool)
                if 'error' in base_solution or 'error' in exp_solution:
                    raise RuntimeError(f'Optimizer failed in GW{week}')
                squad[str(week)] = {variant:{'actual':score_solution(solution,actual),
                    'predicted':solution['expected_fantasy_points'],
                    'xi_ids':[p['id'] for p in solution['starting_xi']],
                    'captain_id':solution['captain']['id'],
                    'bench_ids':[p['id'] for p in solution['squad'] if p['id'] not in
                                 {q['id'] for q in solution['starting_xi']}]} for variant,solution in
                    [('baseline',base_solution),('experimental',exp_solution)]}
    result = {'classification':'offline_retrospective_bonus_experiment',
        'source_retrieved_at':fetched['retrieved_at'], 'coverage':coverage,
        'official_rules_url':'https://tfffantezilig.com/yardim?tab=kurallar-1',
        'gw11_contributions':contributions,'high_actual_excluded':high,
        'walkforward_player_metrics':metrics,'baseline_5w_squad_scores':squad,
        'warnings':['All histories were retrieved after GW11; predeadline publication not verified',
            'Historical player club and price metadata are not verified at each prior deadline',
            'Experimental bonus feature uses only rows strictly before each target week',
            'Squad backtest omits fixtures, availability, automatic substitutions and chips']}
    (ROOT/'phase34_bonus_prediction_audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    report(result)
    return result


def report(d):
    c=d['coverage']; x=d['gw11_contributions']; m=d['walkforward_player_metrics']; s=d['baseline_5w_squad_scores']
    lines=['# Phase 34 — bonus prediction audit','',
        '## Verified source and scoring semantics','',
        f'The [official TFF rules]({d["official_rules_url"]}) award 3, 2 and 1 bonus points to the three highest-scoring players in a match (ties may share a tier). The official history has `points`, `bonus`, and event `breakdown` fields. Of {c["rows"]} GW1–11 player-week rows, {c["with_points"]} have points and {c["with_bonus"]} have bonus; {c["nonzero_bonus"]} have positive bonus. {c["breakdown_rows"]} rows contain event breakdowns and {c["breakdown_point_mismatches"]} disagree with `points` when subtotalled. Thus official `points` includes bonus. Base fantasy points are computed as `points - bonus` only where both fields exist. No bonus is added to official actual totals twice.','',
        'The production `project()` function forecasts from historical `points` and therefore already incorporates realized historical bonus implicitly. It does not have a separate expected-bonus feature. The experimental forecast removes bonus from each pre-target history row, runs the unchanged projection on base points, and adds a five-week mean of past bonus scaled by past minutes. It never reads target-week bonus before prediction. No production weights were changed.','',
        '## GW11 bonus accounting','',
        '| Squad | XI bonus | Captain extra bonus | Total bonus in project score |', '| --- | ---: | ---: | ---: |']
    for name in ('human','baseline_5w','short_form_3w','stable_8w','uniform_xg','position_aware_xg','rest_days_control'):
        a=x[name];lines.append(f'| {name} | {a["xi_bonus"]} | {a["captain_extra_bonus"]} | {a["total_bonus_with_captain"]} |')
    lines += ['',f'Murillo’s reported automatic substitution adds {x["human_murillo_bonus"]} bonus point(s) within his five official points. The project model evaluator omits substitutions; the human 105-point score includes Murillo. Player-level points, base and bonus are in the JSON artifact.','',
        'Highest actual scorers absent from every model XI (bonus shown separately): ' + ', '.join(f'{p["name"]} {p["points"]} total / {p["bonus"]} bonus' for p in d['high_actual_excluded'][:8]) + '.','',
        '## Multiweek player accuracy','',
        '| GW | Model | N | Baseline MAE / RMSE | Experimental MAE / RMSE |', '| ---: | --- | ---: | ---: | ---: |']
    for week in WEEKS:
        for name in MODELS_TESTED:
            a=m[str(week)][name];b=a['baseline'];e=a['experimental']
            lines.append(f'| {week} | {name} | {b["n"]} | {b["mae"]:.3f} / {b["rmse"]:.3f} | {e["mae"]:.3f} / {e["rmse"]:.3f} |')
    lines += ['', '## Baseline 5W squad sensitivity','',
        '| GW | Baseline XI actual | Bonus-aware XI actual | Baseline captain | Bonus-aware captain | XI overlap |',
        '| ---: | ---: | ---: | ---: | ---: | ---: |']
    for week in WEEKS:
        a=s[str(week)]['baseline'];e=s[str(week)]['experimental']
        lines.append(f'| {week} | {a["actual"]} | {e["actual"]} | {a["captain_id"]} | {e["captain_id"]} | {len(set(a["xi_ids"])&set(e["xi_ids"]))}/11 |')
    lines += ['', 'These are exploratory retrospective squads using the same candidates per week. Their player club and price metadata are not independently verified at each historical deadline, and fixture/availability inputs are absent. The squad scores should not be read as prospective performance. GW11 model lineups in Phase 32 are separate saved retrospective results.','',
        '## Free-data next steps','',
        '1. Capture timestamped official player histories and finalized bonus breakdowns weekly. This permits leak-free rolling validation.',
        '2. Capture pre-deadline starting-XI and injury notices from official club or league channels with publication timestamps; bonus opportunities depend on playing time.',
        '3. Capture free match-level shots, chances, saves and team scoring events where rights and coverage permit. Verify entity matching and point-in-time availability before testing player bonus signals.',
        '4. Evaluate bonus calibration over more weeks and compare the same player cohort before considering any production integration. No paid API or GW11-specific tuning is recommended.','',
        '## Limits','',
        'Official histories were fetched after GW11 and may have later corrections. The experiment uses lagged rows only, but their actual pre-deadline publication is unverified. Price, club and availability histories are incomplete; historical squad scores are approximate. No target-week bonus entered any target-week forecast, and no frozen prediction was overwritten.','']
    (ROOT/'phase34_bonus_prediction_audit.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    r=run();print(r['coverage'])
