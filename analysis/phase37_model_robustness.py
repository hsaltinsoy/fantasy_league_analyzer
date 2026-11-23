"""Read-only robustness and decision attribution for the Phase 36 experiment."""
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev

SOURCE=Path('docs/phase36_free_external_data.json')
OUT=Path('docs/phase37_model_robustness.json')
REPORT=Path('docs/phase37_model_robustness.md')
VARIANTS=('baseline','team_form','opponent_defense','combined')


def attribution(base, other):
    a={p['id']:p for p in base['xi_players']}
    b={p['id']:p for p in other['xi_players']}
    base_only=sorted(a.keys()-b.keys())
    other_only=sorted(b.keys()-a.keys())
    shared=sorted(a.keys()&b.keys())
    xi_delta=sum(b[i]['actual'] for i in other_only)-sum(a[i]['actual'] for i in base_only)
    captain_delta=other['captain_actual']-base['captain_actual']
    total_delta=other['actual_squad_points']-base['actual_squad_points']
    assert len(a)==len(b)==11
    assert sum(p['actual'] for p in a.values())+base['captain_actual']==base['actual_squad_points']
    assert sum(p['actual'] for p in b.values())+other['captain_actual']==other['actual_squad_points']
    assert xi_delta+captain_delta==total_delta
    return {'shared_ids':shared,'baseline_only':[a[i] for i in base_only],
            'experimental_only':[b[i] for i in other_only],
            'xi_actual_delta':xi_delta,'captain_actual_delta':captain_delta,
            'total_actual_delta':total_delta}


def run():
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    weekly={}
    player_contributions=defaultdict(float)
    for week,entry in source['historical_experiments'].items():
        base=entry['variants']['baseline']
        variants={}
        for name in VARIANTS:
            row=entry['variants'][name]
            decision=attribution(base,row)
            variants[name]={**decision,'predicted_points':row['predicted_squad_points'],
                'actual_points':row['actual_squad_points'],'captain_id':row['captain_id'],
                'captain_actual':row['captain_actual'],'formation':row['formation'],
                'xi_overlap':len(decision['shared_ids']),
                'player_mae':row['mae'],'player_rmse':row['rmse'],
                'zero_minute_starters':row['zero_minute_starters'],
                'missing_feature_candidates':row['missing_feature_candidates']}
            if name=='combined':
                for p in decision['experimental_only']:
                    player_contributions[str(p['id'])]+=p['actual']
                for p in decision['baseline_only']:
                    player_contributions[str(p['id'])]-=p['actual']
        weekly[week]={'cutoff_date':entry['cutoff_date'],
                      'prior_matches':entry['prior_match_count'],'variants':variants}
    diffs=[weekly[w]['variants']['combined']['total_actual_delta'] for w in sorted(weekly,key=int)]
    total=sum(diffs)
    xi_total=sum(weekly[w]['variants']['combined']['xi_actual_delta'] for w in weekly)
    cap_total=sum(weekly[w]['variants']['combined']['captain_actual_delta'] for w in weekly)
    assert xi_total+cap_total==total==6
    stats={'weekly_differences':diffs,'total':total,
        'wins':sum(x>0 for x in diffs),'losses':sum(x<0 for x in diffs),
        'ties':sum(x==0 for x in diffs),'mean':round(mean(diffs),3),
        'median':round(median(diffs),3),'sample_stddev':round(stdev(diffs),3),
        'xi_total':xi_total,'captain_total':cap_total,
        'leave_one_week_out':{w:total-weekly[w]['variants']['combined']['total_actual_delta'] for w in weekly},
        'player_accounting_contributions':dict(sorted(player_contributions.items(),
                                  key=lambda item:-abs(item[1]))),
        'leave_one_player_contribution_out':{pid:total-value for pid,value in player_contributions.items()},
        'mean_player_mae_delta':round(mean(weekly[w]['variants']['combined']['player_mae']-
                                          weekly[w]['variants']['baseline']['player_mae'] for w in weekly),4),
        'mean_player_rmse_delta':round(mean(weekly[w]['variants']['combined']['player_rmse']-
                                           weekly[w]['variants']['baseline']['player_rmse'] for w in weekly),4)}
    result={'classification':'retrospective_robustness_not_prospective','phase36_source_sha256':source['source_csv_sha256'],
        'source_observed_at':source['source_observed_at'],'weekly':weekly,'robustness':stats,
        'feature_availability':{'verified_predeadline_external_rows':0,
            'retrospectively_observed_matches':source['matched_csv_fixtures'],
            'event_date_filtered':True,
            'team_xg_goals_shots_sot':'retrospectively_obtained; prior match date but publication time unverified',
            'opponent_and_venue':'fixture archive captured 2026-10-28; earlier-week prospective availability unverified',
            'player_club_price_availability':'current/archive proxy; deadline-time historical status unverified'},
        'warnings':source['warnings']+['Six weekly observations do not support significance claims',
            'Player-removal accounting is not a reoptimized squad counterfactual']}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    report(result)
    return result


def report(d):
    weekly=d['weekly'];s=d['robustness']
    lines=['# Phase 37 — multiweek external-model robustness','',
        '**Classification:** retrospective robustness audit of the Phase 36 local experiment; no prospective improvement claim.','',
        '## GW6–11 weekly score comparison','',
        '| GW | Variant | Predicted XI+C | Actual XI+C | Δ actual vs baseline | Captain ID (actual) | Formation | XI overlap | MAE / RMSE |',
        '| ---: | --- | ---: | ---: | ---: | --- | --- | ---: | --- |']
    for week in sorted(weekly,key=int):
        for name in VARIANTS:
            v=weekly[week]['variants'][name]
            lines.append(f'| {week} | {name} | {v["predicted_points"]:.2f} | {v["actual_points"]:.0f} | {v["total_actual_delta"]:+.0f} | {v["captain_id"]} ({v["captain_actual"]:.0f}) | {v["formation"]} | {v["xi_overlap"]}/11 | {v["player_mae"]:.3f} / {v["player_rmse"]:.3f} |')
    lines+=['','## Combined versus baseline attribution','',
        '| GW | Combined − baseline | XI player Δ | Captain Δ | Baseline-only players (actual) | Combined-only players (actual) |',
        '| ---: | ---: | ---: | ---: | --- | --- |']
    for week in sorted(weekly,key=int):
        a=weekly[week]['variants']['combined']
        fmt=lambda rows:', '.join(f'{p["name"]} ({p["id"]}): {p["actual"]} actual / {p["predicted"]:.2f} predicted' for p in rows) or 'none'
        lines.append(f'| {week} | {a["total_actual_delta"]:+.0f} | {a["xi_actual_delta"]:+.0f} | {a["captain_actual_delta"]:+.0f} | {fmt(a["baseline_only"])} | {fmt(a["experimental_only"])} |')
    lines+=['',f'Combined advantage **{s["total"]:+.0f}** = XI changes {s["xi_total"]:+.0f} + captain changes {s["captain_total"]:+.0f}. Every weekly and total decomposition reconciles exactly. Shared players cancel. No bench substitution or chip is modeled.','',
        '## Robustness','',
        f'Weekly wins/losses/ties: **{s["wins"]}/{s["losses"]}/{s["ties"]}**. Mean difference {s["mean"]:+.3f}, median {s["median"]:+.3f}, sample standard deviation {s["sample_stddev"]:.3f}. Mean player-level MAE delta {s["mean_player_mae_delta"]:+.4f}; RMSE delta {s["mean_player_rmse_delta"]:+.4f} (combined minus baseline).','',
        '| Omitted GW | Remaining combined advantage |','| ---: | ---: |']
    for week,value in s['leave_one_week_out'].items():lines.append(f'| {week} | {value:+.0f} |')
    lines+=['','The leave-one-week-out range shows that removing GW7 reverses the advantage. Six weeks are insufficient for a significance or superiority claim. The GW11 baseline here scored 70 under the Phase 36 historical pool and feature setup; it is a different experiment from the Phase 32 GW11 baseline lineup that scored 75. These scores must not be merged.','',
        '### Individual-player accounting sensitivity','',
        'The values below remove one player’s observed contribution from lineup-difference arithmetic across weeks. They **do not** reoptimize either squad and are not attainable counterfactual scores.','',
        '| Player ID | Net lineup-difference contribution | Combined advantage without contribution |',
        '| ---: | ---: | ---: |']
    for pid,value in list(s['player_accounting_contributions'].items())[:12]:
        lines.append(f'| {pid} | {value:+.0f} | {s["leave_one_player_contribution_out"][pid]:+.0f} |')
    lines+=['','## Data rights and leakage audit','',
        '| Feature | Historical availability classification |','| --- | --- |',
        '| Team goals, xG, shots, shots on target | Matches are dated before each target GW; CSV bytes were first observed after GW11. Publication by each earlier deadline is **unverified**. |',
        '| Opponent strength and home/away form | Derived from the same retrospectively obtained CSV; publication timing unverified. |',
        '| Target fixture/opponent | Official fixture archive was captured 2026-10-28; earlier GW6–9 pre-deadline snapshot unavailable. |',
        '| Player club, price, availability | Historical deadline-time snapshots unavailable; retrospective proxy. |','',
        'The [Football-Data fair-use policy](https://football-data.co.uk/contact.php) limits free use to light personal/academic access and does not grant commercial or heavy AI training use. No new CSV download occurred in this audit. These features must not be promoted into production from this evidence.','',
        '## Recommendation','',
        'Continue combined-feature experiments only on newly timestamped, permitted pre-deadline captures. Prioritize expected-minutes and status calibration because Phase 35 found consequential zero-minute errors; then assess captain decisions and team features on the same prospective weeks. No alternative free provider has measured player/lineup coverage and confirmed reuse rights here, so switching provider now is unsupported. Wait for genuine prospective results before changing production weights.','',
        'Focused tests verify exact score decomposition, leave-one-week-out accounting and source-cutoff handling. Frozen predictions and production settings were untouched.','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    print(run()['robustness'])
