"""Offline GW6–11 participation audit; no production predictions or API requests."""
import json
from collections import defaultdict
from math import sqrt
from pathlib import Path
from statistics import mean

from analysis.multiweek_backtest import MODELS, project
from analysis.walkforward_backtest import participation

ROOT=Path('docs')
WEEKS=range(6,12)


def alternative(past):
    """Untrained Laplace-smoothed recent appearance frequency; experimental only."""
    last=past[-4:]
    return (1+sum(float(r.get('minutesPlayed') or 0)>0 for r in last))/(2+len(last))


def scores(rows, key, threshold):
    tp=sum(r[key]>=threshold and r['played'] for r in rows)
    fp=sum(r[key]>=threshold and not r['played'] for r in rows)
    tn=sum(r[key]<threshold and not r['played'] for r in rows)
    fn=sum(r[key]<threshold and r['played'] for r in rows)
    return {'n':len(rows),'tp':tp,'fp':fp,'tn':tn,'fn':fn,
            'accuracy':round((tp+tn)/len(rows),3),
            'precision':round(tp/(tp+fp),3) if tp+fp else None,
            'recall':round(tp/(tp+fn),3) if tp+fn else None,
            'brier':round(mean((r[key]-int(r['played']))**2 for r in rows),3),
            'mae':round(mean(abs(r[key]-int(r['played'])) for r in rows),3)}


def run():
    fetched=json.loads((ROOT/'phase28_official_histories.json').read_text(encoding='utf-8'))
    source=fetched['rows_by_player']
    players={str(p['id']):p for p in json.loads(Path('historical_data/players.json').read_text(encoding='utf-8'))}
    observations=[]
    for pid,p in players.items():
        rows=source.get(pid,[])
        for week in WEEKS:
            past=[r for r in rows if int(r['gameweekOrder'])<week]
            target=next((r for r in rows if int(r['gameweekOrder'])==week),None)
            if not past or target is None:continue
            proxy=participation(past)
            observations.append({'id':int(pid),'name':p['name'],'position':p['position'],
                'week':week,'proxy':proxy['probability'],'alternative':alternative(past),
                'avg_last4_minutes':proxy['avg_minutes'],'starts_rate':proxy['starts_rate'],
                'predicted_xpts':project(p,past,MODELS['baseline_5w']),
                'minutes':target['minutesPlayed'],'played':target['minutesPlayed']>0,
                'started':bool(target.get('started')),'actual_points':target['points'],
                'prior_minutes':[r.get('minutesPlayed') for r in past[-4:]]})
    by_week={str(w):{'proxy':scores([r for r in observations if r['week']==w],'proxy',.5),
                     'alternative':scores([r for r in observations if r['week']==w],'alternative',.5),
                     'gate':scores([r for r in observations if r['week']==w],'proxy',.25)}
             for w in WEEKS}
    def bins(key):
        return [{'lower':i/10,'upper':(i+1)/10,'n':len(group),
                 'mean_prediction':round(mean(r[key] for r in group),3) if group else None,
                 'observed_rate':round(mean(r['played'] for r in group),3) if group else None}
                for i in range(10) for group in [[r for r in observations if min(9,int(r[key]*10))==i]]]
    zero=sorted((r for r in observations if r['week']==11 and not r['played']),key=lambda r:-r['predicted_xpts'])[:20]
    missed=sorted((r for r in observations if r['week']==11 and r['proxy']<.25 and r['minutes']>=60),
                  key=lambda r:-r['actual_points'])[:20]
    missed_count=sum(r['week']==11 and r['proxy']<.25 and r['minutes']>=60 for r in observations)
    category={}
    for label,predicate in [('zero',lambda r:r['minutes']==0),('under60',lambda r:0<r['minutes']<60),
                             ('60plus',lambda r:r['minutes']>=60)]:
        group=[r for r in observations if predicate(r)]
        category[label]={'n':len(group),'mae_xpts':round(mean(abs(r['predicted_xpts']-r['actual_points']) for r in group),3),
                         'mean_xpts':round(mean(r['predicted_xpts'] for r in group),3),
                         'mean_actual':round(mean(r['actual_points'] for r in group),3)}
    all_metrics={key:scores(observations,key,.5) for key in ('proxy','alternative')}
    result={'classification':'approximate_historical_participation_audit','observed_at':fetched['retrieved_at'],
        'population':len(players),'player_weeks':len(observations),'weeks':list(WEEKS),
        'metrics':all_metrics,'by_week':by_week,'calibration':{'proxy':bins('proxy'),'alternative':bins('alternative')},
        'fantasy_error_by_minutes':category,'gw11_high_projection_zero_minutes':zero,
        'gw11_excluded_60plus_minutes':missed,
        'gw11_excluded_60plus_count':missed_count,
        'gw11_osimhen':next(r for r in observations if r['week']==11 and r['id']==507),
        'warnings':['Proxy is a heuristic, not a trained probability',
            'No production expected-minutes forecast is persisted for lineup models',
            'All history rows retrieved after GW11; historical source publication time unverified',
            'Historical player availability/status and club metadata at each deadline unavailable',
            'Current player archive used only for ID, name, position; transferred positions may be stale']}
    (ROOT/'phase35_player_availability_audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    report(result)
    return result


def report(d):
    lines=['# Phase 35 — player availability and expected-minutes audit','',
      '**Classification:** approximate retrospective GW6–11 evaluation. The six Phase 32 GW11 squads and saved prospective predictions remain unchanged.','',
      '## Current implementation','',
      '`participation()` uses the last four available rows: 0.65 × played-match share + 0.35 × min(1, mean minutes / 75), clamped to 0.05–1.00. A player enters the new-lineup candidate pool at 0.25. This is a heuristic score, **not a calibrated probability**. It reports recent average minutes and starts rate, but the production lineup model does not emit an explicit expected-minutes forecast or a separate zero-minute probability. `project()` multiplies form by min(1, recent mean minutes / 85), so recent minutes already affect xPts. The official status gate excludes blocked labels and discounts doubtful ones; historical deadline-time statuses were not archived.','',
      'The dashboard has a separate expected-minutes blend in `production_scoring.py`; it is not the six lineup models. No stored per-player minute forecast exists for those models, so expected-minutes MAE cannot be validly reported. Last-four mean minutes are a descriptive proxy, not a forecast. The `started` history field enters the audit but not the lineup eligibility formula.','',
      '## Historical participation metrics','',
      f'{d["player_weeks"]} player-weeks across GW6–11, drawn from {d["population"]} current archived IDs. Actual participation is minutes > 0. Threshold 0.50 measures classifier performance; the 0.25 row measures the actual eligibility gate. Brier scores are descriptive because neither score was trained/calibrated as a probability.','',
      '| GW | Proxy accuracy | Proxy FP / FN | Proxy Brier | Alt accuracy | Alt FP / FN | Gate FP / FN |',
      '| ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for w in WEEKS:
        m=d['by_week'][str(w)]
        lines.append(f'| {w} | {m["proxy"]["accuracy"]:.3f} | {m["proxy"]["fp"]} / {m["proxy"]["fn"]} | {m["proxy"]["brier"]:.3f} | {m["alternative"]["accuracy"]:.3f} | {m["alternative"]["fp"]} / {m["alternative"]["fn"]} | {m["gate"]["fp"]} / {m["gate"]["fn"]} |')
    lines += ['',f'Across all weeks: proxy Brier {d["metrics"]["proxy"]["brier"]:.3f}, accuracy {d["metrics"]["proxy"]["accuracy"]:.3f}; fixed Laplace-smoothed last-four appearance frequency Brier {d["metrics"]["alternative"]["brier"]:.3f}, accuracy {d["metrics"]["alternative"]["accuracy"]:.3f}. This alternative is an untrained experimental benchmark, never integrated into production. Calibration-bin counts and observed rates are in JSON.','',
      '## Fantasy errors by realized minutes','',
      '| Minutes category | N | Mean predicted xPts | Mean actual | MAE |','| --- | ---: | ---: | ---: | ---: |']
    for key,value in d['fantasy_error_by_minutes'].items():
        lines.append(f'| {key} | {value["n"]} | {value["mean_xpts"]:.3f} | {value["mean_actual"]:.3f} | {value["mae_xpts"]:.3f} |')
    o=d['gw11_osimhen']
    lines += ['',f'**Osimhen GW11:** prior minutes {o["prior_minutes"]}; proxy {o["proxy"]:.3f}, 0.25 gate passed; unadjusted baseline form xPts {o["predicted_xpts"]:.3f}; actual {o["minutes"]} minutes and {o["actual_points"]} points. This unadjusted historical projection is not the Phase 32 fixture-adjusted lineup xPts. His GW11 absence is verified, but no timestamped pre-deadline injury, rotation or lineup notice was preserved, so its predictability is unknown.','',
      '### GW11 highest projected zero-minute players','',
      '| Player | xPts | Proxy | Prior four minutes | Actual minutes |','| --- | ---: | ---: | --- | ---: |']
    for r in d['gw11_high_projection_zero_minutes'][:10]:
        lines.append(f'| {r["name"]} ({r["id"]}) | {r["predicted_xpts"]:.3f} | {r["proxy"]:.3f} | {r["prior_minutes"]} | {r["minutes"]} |')
    lines += ['',f'GW11 players below the 0.25 gate who nevertheless played 60+ minutes: {d["gw11_excluded_60plus_count"]} (top 20 retained in JSON). These are retrospective false exclusions; historical availability and eligibility at the deadline are unknown.','',
      '## Free-source evidence and limitations','',
      '| Source | Actual Turkish-league evidence | Timestamp / historical limit | Use |','| --- | --- | --- | --- |',
      '| Official TFF Fantasy history and status | 573 GW11 player rows and live statuses observed in prior project audits | Histories retrieved after GW11; status has no archived deadline-time revisions | Minutes, starts, suspensions/status when timestamped prospectively |',
      '| [TFF discipline decisions](https://www.tff.org/Default.aspx?pageID=238) | Public dated 2026 Süper Lig decisions are visible | Publication dates exist; player-ID linking and effective ban dates need validation | Prospective suspension flags only after publication |',
      '| [Official TFF Fantasy rules](https://tfffantezilig.com/yardim) | League-specific lineup/auto-sub rules verified | Rules page is current, not historical lineup feed | Scoring and replacement eligibility |',
      '| Club announcements / official match lineups | No measured 2026–27 coverage in this audit | Timing relative to fantasy deadline unverified | Research-only until a dated, licensed source and ID matching are validated |',
      'No free source in this audit has verified historical pre-deadline injury, expected-minutes or lineup coverage for the full 573-player population. No paid API or unauthorized scraping was used. Public pages were inspected read-only; automated reuse terms were not established.','',
      '## Recommended next steps','',
      '1. Persist official player status, timestamped club notices and the current candidate pool before each deadline. Validate effective suspension dates and player-ID matches.',
      '2. Save an explicit expected-minutes and zero-minute estimate with each future prediction, then calibrate them on genuinely prospective weeks.',
      '3. Backtest any experimental appearance model across more weeks and with deadline-time status evidence before replacing the current gate. The simple Laplace benchmark here is diagnostic, not a production recommendation.',
      '4. Separate injury, suspension, rest and tactical rotation only when a timestamped pre-deadline source identifies the reason. Do not infer a known absence from postmatch zero minutes.','',
      '## Data quality','',
      'Player histories were obtained after the evaluated weeks; publication timing and later corrections are unknown. Historical prices, clubs and availability are not point-in-time verified. Metrics use lagged numerical histories only and current archived identity labels. No model weights, frozen snapshots or saved predictions changed.','']
    (ROOT/'phase35_player_availability_audit.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    r=run();print(r['player_weeks'],r['metrics'])
