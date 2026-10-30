"""Next-week XI using historical form and current official player prices/status."""
import argparse,json
import os
from pathlib import Path
from datetime import datetime,timezone
from analysis.multiweek_backtest import load_history, MODELS, project
from analysis.walkforward_backtest import participation
from analysis.walkforward_v27 import fixture_multipliers
from analysis.verified_fixtures_v34 import load_verified
from analysis.verified_fixtures_v36 import make_optimizer
from analysis.availability import evaluate as evaluate_availability
from analysis.team_of_week_v36 import load as load_tow
from analysis.production_scoring import lineup_player_points

STORE=Path('historical_data')

def build_candidate_pool(week,players,records,fixtures,model='short_form_3w',fixture_weight=.5):
    """Production eligibility and xPts calculation, exposed for read-only experiments."""
    history={int(p['id']):rows for p,rows in records}
    strengths=fixture_multipliers(records,week)
    pool=[]
    excluded={'history':0,'fixture':0,'minutes':0,'availability':0,'price':0}
    for p in players:
        past=[r for r in history.get(int(p['id']),[]) if int(r['gameweekOrder'])<week]
        if not past:excluded['history']+=1;continue
        club=str(p.get('club_id') or p.get('team') or '')
        opponent=fixtures[week].get(club)
        if opponent is None:excluded['fixture']+=1;continue
        probability=participation(past)['probability']
        if probability<.25:excluded['minutes']+=1;continue
        availability=evaluate_availability(p,round_number=week)
        if not availability['eligible'] or availability['factor']<.25:
            excluded['availability']+=1;continue
        try:price=float(p['price'])
        except (ValueError,TypeError):excluded['price']+=1;continue
        if price<=0:excluded['price']+=1;continue
        factor=strengths.get((opponent,p['position']),1.)
        points=lineup_player_points(p,past,model,1+fixture_weight*(factor-1),availability['factor'])
        pool.append({'id':int(p['id']),'name':p['name'],'team':club,'position':p['position'],
            'price':price,'xpts':points,'opponent':opponent,
            'participation_probability':probability,'availability_factor':availability['factor']})
    return pool, excluded


def predict(week,players,records,fixtures,tow,model='short_form_3w',fixture_weight=.5,tow_weight=0.,risk_profile='balanced',experimental_covariance=False,fixture_archive=None):
    pool, excluded=build_candidate_pool(week,players,records,fixtures,model,fixture_weight)
    if len(pool)<15:raise ValueError(f'Not enough players: {len(pool)}, exclusions: {excluded}')
    from analysis.optimizer import optimize
    def risk_optimize(items):
        return optimize(items,risk_profile=risk_profile)
    solution=make_optimizer(records,week,.2,.15,tow,tow_weight,optimizer_func=risk_optimize)(pool)
    if 'error' in solution:raise RuntimeError(solution['error'])
    ids={p['id'] for p in solution['starting_xi']}
    order={'GK':0,'DEF':1,'MID':2,'FWD':3}
    xi=sorted((dict(p,captain=p['id']==solution['captain']['id']) for p in solution['starting_xi']),key=lambda p:(order[p['position']],-p['xpts']))
    bench=sorted((p for p in solution['squad'] if p['id'] not in ids),key=lambda p:(order[p['position']],-p['xpts']))
    captain_bonus=solution['captain'].get('captain_bonus_xpts',solution['captain']['xpts'])
    result={'optimization_status':solution.get('status'),'all_formations_proven_optimal':solution.get('all_formations_proven_optimal'),
        'captain_bonus_xpts':captain_bonus,
        'captain_alternatives':sorted([{'id':q['id'],'name':q['name'],'xpts':q['xpts'],
           'captain_bonus_xpts':q.get('captain_bonus_xpts',q['xpts'])} for q in solution['starting_xi']],
           key=lambda q:-q['captain_bonus_xpts'])[:5],
        'budget_remaining':round(100-solution['squad_cost'],2),
        'risk_profile':risk_profile,'risk_penalty':solution.get('risk_penalty',0),
        'opposing_pairs':solution.get('opposing_pairs',[]),
        'risk_adjusted_objective':solution.get('risk_adjusted_objective'),
        'week':week,'generated_utc':datetime.now(timezone.utc).isoformat(),
        'model':model,'formation':solution['formation'],'expected_points':solution['expected_points'],
        'captain':solution['captain']['name'],'cost':solution['squad_cost'],
        'starting_xi':xi,'bench':bench,'eligible_players':len(pool),'excluded':excluded,
        'formation_comparison':solution['formation_comparison'],
        'warning':'Forecast only. No existing-team transfers/chips. Historical snapshots and fixture file may be stale.'}
    from analysis.lineup_diagnostics import describe
    result['diagnostics']=describe(result)
    if experimental_covariance:
        from analysis.experimental_covariance import estimate, compare_candidates
        raw_fixtures=fixture_archive if fixture_archive is not None else json.loads((STORE/'tff_fixtures_verified_v5.json').read_text(encoding='utf-8'))
        evidence=estimate(records,raw_fixtures['weeks'],week)
        result['experimental_covariance']={'evidence':evidence,
            'comparison':compare_candidates(solution['formation_solutions'],evidence)}
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--week',type=int,default=10)
    parser.add_argument('--risk-profile',choices=['aggressive','balanced','cautious'],default='balanced')
    parser.add_argument('--live',action='store_true',help='Fetch current prices/status from official TFF')
    parser.add_argument('--model',choices=sorted(MODELS),default='short_form_3w')
    parser.add_argument('--tow-weight',type=float,default=0.)
    parser.add_argument('--experimental-covariance',action='store_true')
    parser.add_argument('--as-of', help='ISO 8601 evidence cutoff for a historical forecast')
    args=parser.parse_args()
    if os.environ.get('STORAGE_BACKEND', 'postgres').lower() == 'postgres':
        from storage.db import engine_from_env
        from storage.runtime_repository import RuntimeRepository
        repository = RuntimeRepository(engine_from_env())
        players = repository.current_player_pool(max_age_seconds=3600)
        archive = repository.fixture_archive(max_age_seconds=3600)
        from analysis.live_benchmark import _fixture_lookup
        entry = archive['weeks'].get(str(args.week))
        if not entry:
            raise ValueError(f'No PostgreSQL fixture entry for GW{args.week}')
        from analysis.prediction_tracking import parse_time
        deadline = parse_time(entry.get('deadline'))
        cutoff = parse_time(args.as_of) if args.as_of else None
        if args.as_of and cutoff is None:
            raise ValueError('--as-of must include a timezone')
        if cutoff is not None:
            raise ValueError('Historical PostgreSQL forecast requires dated player-state evidence; current pool cannot satisfy --as-of')
        if deadline and deadline <= datetime.now(timezone.utc):
            raise ValueError('Historical PostgreSQL forecast requires a dated player-state snapshot; current pool is not deadline evidence')
        histories = repository.historical_records(before_week=args.week, as_of=cutoff)
        records = [(player, histories.get(str(player['id']), [])) for player in players]
        fixtures = {args.week: _fixture_lookup(entry)}
        tow = repository.team_of_week() if args.tow_weight else {}
        result = predict(args.week, players, records, fixtures, tow, args.model,
            tow_weight=args.tow_weight, risk_profile=args.risk_profile,
            experimental_covariance=args.experimental_covariance,
            fixture_archive=archive)
        from analysis.prediction_tracking import save_snapshot, save_prediction
        from storage.repository import tracking_transaction
        with tracking_transaction(repository.engine):
            snapshot = save_snapshot(args.week, players, entry['matches'],
                [{'player_id': player['id'], 'rows': histories.get(str(player['id']), [])}
                 for player in players],
                {'players': 'postgres_current_official_api',
                 'fixtures': archive['source_url'],
                 'fixtures_retrieved_at': archive['captured_utc'],
                 'histories': 'postgres_source_payloads'},
                deadline_at=entry.get('deadline'), deadline_source=archive['source_url'])
            result['prediction_tracking'] = save_prediction(snapshot['id'], result,
                model_version='v3.9')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.live:
        from data_sources.tff_official import fetch_players
        players=fetch_players()['players']
    else:
        players=json.loads((STORE/'players.json').read_text(encoding='utf-8'))
        print('WARNING: saved player prices/status, not live')
    records=load_history()
    fixtures=load_verified(STORE/'tff_fixtures_verified_v5.json',[args.week])
    tow=load_tow(STORE/'team_of_week_verified.json')
    result=predict(args.week,players,records,fixtures,tow,args.model,tow_weight=args.tow_weight,risk_profile=args.risk_profile,experimental_covariance=args.experimental_covariance)
    path=STORE/f'next_week_gw{args.week}.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"\nGW{args.week} | {result['formation']} | {result['expected_points']} projected points | {result['cost']} budget")
    print('CAPTAIN:',result['captain'])
    for section in ('starting_xi','bench'):
        print('\n'+section.upper())
        for p in result[section]:
            print(f"{p['position']:3} {p['name'][:38]:38} {p['xpts']:5.2f} pts  price {p['price']:.1f}  opponent {p['opponent']}" + (' (C)' if p.get('captain') else ''))
    print('\nJSON:',path)
if __name__=='__main__':main()
