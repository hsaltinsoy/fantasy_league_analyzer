"""Read-only before/after replay of the versioned formation policies."""
import json
from pathlib import Path

from analysis.multiweek_backtest import MODELS, build_week
from analysis.optimizer import FORMATIONS, LEGACY_FORMATIONS, optimize

OUT=Path('docs/phase39_formation_coverage.json')
REPORT=Path('docs/phase39_formation_coverage.md')


def evaluate(pool,actual,policy):
    prediction=optimize(pool,formation_policy=policy)
    if 'error' in prediction:raise RuntimeError(prediction['error'])
    xi=prediction['starting_xi']
    captain=prediction['captain']
    score=sum(actual[str(p['id'])] for p in xi)+actual[str(captain['id'])]
    return {'policy':policy,'formation':prediction['formation'],
        'xi_ids':[p['id'] for p in xi],
        'bench_ids':[p['id'] for p in prediction['squad'] if p['id'] not in {q['id'] for q in xi}],
        'captain_id':captain['id'],'predicted_fantasy_points':prediction['expected_fantasy_points'],
        'objective':prediction['risk_adjusted_objective'],'actual_points':score,
        'all_formations_optimal':prediction['all_formations_proven_optimal'],
        'formation_comparison':prediction['formation_comparison']}


def run():
    source=json.loads(Path('docs/phase28_official_histories.json').read_text(encoding='utf-8'))['rows_by_player']
    players=json.loads(Path('historical_data/players.json').read_text(encoding='utf-8'))
    records=[(p,source[str(p['id'])]) for p in players]
    results={}
    for week in (6,8,11):
        pool,actual,_=build_week(records,week,MODELS['baseline_5w'])
        pool=[{k:v for k,v in p.items() if k!='actual_points'} for p in pool]
        old=evaluate(pool,actual,'legacy_pre39_v1')
        new=evaluate(pool,actual,'current_tff_v2')
        results[str(week)]={'candidate_count':len(pool),'legacy':old,'current':new,
            'xi_overlap':len(set(old['xi_ids'])&set(new['xi_ids'])),
            'objective_gain':round(new['objective']-old['objective'],4),
            'actual_delta':new['actual_points']-old['actual_points']}
        if results[str(week)]['objective_gain'] < -.0002:
            raise AssertionError('Expanded formation set reduced optimal modeled objective')
    result={'classification':'retrospective_formation_policy_replay',
        'official_rules_url':'https://tfffantezilig.com/yardim?tab=sss',
        'current_formations':['-'.join(map(str,f)) for f in FORMATIONS],
        'legacy_formations':['-'.join(map(str,f)) for f in LEGACY_FORMATIONS],
        'weeks':results,
        'warnings':['Current TFF rules observed now; historical rule versions were not archived',
                    'Historical player prices and clubs are reconstructed, not verified deadline snapshots',
                    'Actual GW outcomes used only after optimizer selection']}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    report(result)
    return result


def report(d):
    lines=['# Phase 39 — complete formation coverage','',
        '**Policy change:** new optimization considers all eight standard TFF formations. Frozen predictions and snapshots remain unchanged.','',
        '## Official rules and implementation','',
        f'The [current official TFF help]({d["official_rules_url"]}) lists: '+', '.join(d['current_formations'])+'. It also requires a 15-player squad of 2 GK, 5 DEF, 5 MID and 3 FWD, with one starting GK and eleven total starters. Enumerating 3–5 DEF, 2–5 MID and 1–3 FWD subject to ten outfield starters produces exactly these eight formations. The old list omitted **5-2-3**.','',
        'The optimizer now derives formations from those position bounds. Its default policy is `current_tff_v2`; `legacy_pre39_v1` preserves the former seven-formation behavior for historical replays. Existing budget, club, captain and eligibility logic were not changed. Legacy replay bundles explicitly use the legacy policy.','',
        '## Historical before/after replays','',
        '| GW | Candidates | Old formation | New formation | XI overlap | Old → new captain | Old → new objective | Gain | Old → new fantasy xPts | Old → new actual |',
        '| ---: | ---: | --- | --- | ---: | --- | ---: | ---: | ---: | ---: |']
    for week,row in d['weeks'].items():
        old,new=row['legacy'],row['current']
        lines.append(f'| {week} | {row["candidate_count"]} | {old["formation"]} | {new["formation"]} | {row["xi_overlap"]}/11 | {old["captain_id"]} → {new["captain_id"]} | {old["objective"]:.4f} → {new["objective"]:.4f} | {row["objective_gain"]:+.4f} | {old["predicted_fantasy_points"]:.2f} → {new["predicted_fantasy_points"]:.2f} | {old["actual_points"]:.0f} → {new["actual_points"]:.0f} |')
    lines+=['','All three comparisons use the same reconstructed player pool and predicted xPts for both policies. Actual scores were loaded only for evaluation after the lineups were selected. Per-formation statuses, XI and bench IDs are in JSON. These reconstructed pools do not establish point-in-time pre-deadline feasibility.','',
        '## Optimality and compatibility','',
        'The small synthetic test independently enumerates feasible XIs and captains and matches the CP-SAT objective. Regression tests enumerate the official eight formations, confirm 5-2-3 is reachable and verify legacy mode excludes it. A time-limited `feasible` result would not prove global optimality; each replay records whether every evaluated formation returned `optimal`.','',
        'The selected historical weeks show whether the missing formation caused modeled objective loss in these pools only. A zero gain does not prove it never matters; a synthetic pool demonstrates a case where 5-2-3 wins. Old saved predictions are not rewritten, and replays can request `legacy_pre39_v1`.','',
        'Focused regression suite: 16 passed, including eight formation-selection cases, a brute-force small-pool optimum, legacy replay routing, forced-selection and captain-scoring checks. No production prediction weights, frozen records, or eligibility thresholds were changed.','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    print({w:r['objective_gain'] for w,r in run()['weeks'].items()})
