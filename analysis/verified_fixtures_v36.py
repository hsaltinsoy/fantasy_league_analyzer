"""v3.5 retrospective walk-forward: risk-aware captain + prior-minutes trend.

Run: python -m analysis.verified_fixtures_v35
No target-week information enters player features or model selection.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from analysis.multiweek_backtest import MODELS, load_history
from analysis.walkforward_backtest import evaluate as evaluate_plain
from analysis.walkforward_v32 import evaluate_fixture
from analysis.verified_fixtures_v34 import load_verified, SOURCE
from analysis.team_of_week_v36 import load as load_tow, boost as tow_boost

def minutes_trend(history, week):
    past = sorted((r for r in history if int(r['gameweekOrder']) < week),
                  key=lambda r: int(r['gameweekOrder']))
    from analysis.historical_backtest import number
    mins = [max(0., number(r.get('minutesPlayed'), 0)) for r in past[-4:]]
    if not mins:
        return 0., 0.
    recent = mins[-1]
    prior = mean(mins[:-1]) if len(mins) > 1 else recent
    # Only downweight a recent drop; never infer confirmed injury.
    trend_risk = max(0., min(1., (prior - recent) / 90.))
    no_show = sum(m == 0 for m in mins[-3:]) / min(3,len(mins))
    return trend_risk, no_show

def make_optimizer(records, week, captain_risk, minutes_risk, tow_weeks=None, tow_weight=0., optimizer_func=None):
    from analysis.optimizer import optimize
    histories = {str(p['id']): rows for p, rows in records}
    def wrapped(pool):
        updated = []
        for original in pool:
            p = dict(original)
            trend, no_show = minutes_trend(histories.get(str(p['id']), []), week)
            # The baseline projection already accounts for minutes; use modest
            # *additional* trend penalty only, avoiding a second full scaling.
            p['xpts'] = round(max(.1, p['xpts'] * (1 - minutes_risk * (.65*trend + .35*no_show)) * (tow_boost(tow_weeks,week,int(p['id']),tow_weight) if tow_weeks else 1.0)), 3)
            # Risk-adjust ONLY captain bonus, not the player's XI value.
            # High recent variance and recent non-appearance reduce captain appeal.
            hist = [r for r in histories.get(str(p['id']), []) if int(r['gameweekOrder']) < week]
            from analysis.historical_backtest import number
            recent_pts = [number(r.get('points'), 0) for r in sorted(hist, key=lambda r:int(r['gameweekOrder']))[-5:]]
            volatility = min(1., pstdev(recent_pts) / 12.) if len(recent_pts) > 1 else .5
            p['captain_bonus_xpts'] = round(max(.05, p['xpts'] * (1 - captain_risk*(.65*volatility + .35*no_show))), 3)
            updated.append(p)
        return (optimizer_func or optimize)(updated)
    return wrapped

def choose(rows, risk=.25, error_weight=.12):
    actuals = [r['actual'] for r in rows]
    if any(v is None for v in actuals):
        raise ValueError('Missing historical actuals')
    spread = pstdev(actuals) if len(actuals)>1 else 15.
    return mean(actuals) - risk*spread - error_weight*mean(r['absolute_error'] for r in rows)

def run(records, fixtures, weeks, fixture_weights, captain_risks, minutes_risks, tow_weeks, tow_weights):
    candidates = {
        f'{name}__f{int(fw*100):03d}__c{int(cr*100):03d}__m{int(mr*100):03d}__t{int(tw*100):03d}':(cfg,fw,cr,mr,tw)
        for name,cfg in MODELS.items()
        for fw in fixture_weights for cr in captain_risks for mr in minutes_risks for tw in tow_weights
    }
    cache={}
    for week in weeks:
        for name,(cfg,fw,cr,mr,tw) in candidates.items():
            print(f'GW{week}: {name}',flush=True)
            optimizer=make_optimizer(records,week,cr,mr,tow_weeks,tw)
            if fw==0:
                r=evaluate_plain(records,week,cfg,.25,optimizer)
            else:
                r=evaluate_fixture(records,week,cfg,fixtures[week],fw,.25,optimizer)
            cache[week,name]=r
    steps=[]
    for idx,week in enumerate(weeks):
        prior=weeks[:idx]
        if prior:
            scores={name:choose([cache[w,name] for w in prior]) for name in candidates}
            selected=max(sorted(scores),key=lambda name:scores[name])
            result=cache[week,selected]
            params=candidates[selected]
            selection_score=round(scores[selected],3)
        else:
            selected=result=params=selection_score=None
        steps.append({'week':week,'training_weeks':list(prior),'selected_model':selected,
                      'training_selection_score':selection_score,
                      'fixture_weight':params[1] if params else None,
                      'captain_risk':params[2] if params else None,
                      'minutes_risk':params[3] if params else None,
                      'tow_weight':params[4] if params else None,
                      'result':result,
                      'all_models':{name:{k:cache[week,name][k] for k in ('predicted','actual','absolute_error')}
                                    for name in candidates}})
    scored=[s['result'] for s in steps if s['result'] and s['result']['actual'] is not None]
    return {'created_utc':datetime.now(timezone.utc).isoformat(),
            'classification':'OFFICIAL_LIVE_API_RETROSPECTIVE_NOT_PREDEADLINE_VERIFIED',
            'fixture_mode':'official_live_api_fixture_ids',
            'team_of_week_coverage':sorted(tow_weeks),
            'team_of_week_rule':'Only weeks strictly before target; 0.65 last3 + 0.35 last5; 0 to 10 percent uplift',
            'selection_rule':'past realized points minus 0.25*past SD minus 0.12*past MAE; first week warmup',
            'source_endpoint':SOURCE,'weeks':steps,
            'summary':{'scored_weeks':len(scored),
                       'total_actual':round(sum(r['actual'] for r in scored),2),
                       'mean_actual':round(mean(r['actual'] for r in scored),3) if scored else None,
                       'raw_mae':round(mean(r['absolute_error'] for r in scored),3) if scored else None},
            'limitations':['Retrospective live fixture data, not independently verified pre-deadline snapshots.',
                           'Current club membership and historical prices not point-in-time verified.',
                           'Captain risk uses past fantasy points dispersion, not confirmed injury news.',
                           'No autosubs, chips, transfers or transfer penalties.',
                           'Four scoring weeks is too small for strong generalization claims.']}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixtures',type=Path,default=Path('historical_data/tff_fixtures_verified_v5.json'))
    ap.add_argument('--weeks',nargs='+',type=int,default=[5,6,7,8,9])
    ap.add_argument('--tow-file',type=Path,default=Path('historical_data/team_of_week_verified.json'))
    ap.add_argument('--tow-weights',nargs='+',type=float,default=[0.,.05,.10])
    ap.add_argument('--fixture-weights',nargs='+',type=float,default=[0.,.5])
    ap.add_argument('--captain-risks',nargs='+',type=float,default=[0.,.2])
    ap.add_argument('--minutes-risks',nargs='+',type=float,default=[0.,.15])
    args=ap.parse_args()
    if args.weeks!=sorted(set(args.weeks)) or min(args.weeks)<2:
        ap.error('Weeks must be ascending unique and >=2')
    fixtures=load_verified(args.fixtures,args.weeks)
    tow_weeks=load_tow(args.tow_file)
    report=run(load_history(),fixtures,args.weeks,args.fixture_weights,args.captain_risks,args.minutes_risks,tow_weeks,args.tow_weights)
    out=Path('historical_data');out.mkdir(exist_ok=True)
    jp=out/'walkforward_backtest_v36.json';cp=out/'walkforward_backtest_v36.csv'
    jp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with cp.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['week','model','fixture_weight','captain_risk','minutes_risk','tow_weight','actual','predicted','absolute_error','formation','captain'])
        writer.writeheader()
        for step in report['weeks']:
            if step['result']:
                r=step['result']
                writer.writerow({'week':step['week'],'model':step['selected_model'],
                                 'fixture_weight':step['fixture_weight'],'captain_risk':step['captain_risk'],
                                 'minutes_risk':step['minutes_risk'],'tow_weight':step['tow_weight'],
                                 **{k:r[k] for k in ('actual','predicted','absolute_error','formation','captain')}})
    print('v3.6:',report['summary'],'\nJSON:',jp,'\nCSV:',cp)

if __name__=='__main__':
    main()
