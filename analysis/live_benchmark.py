"""Append-only, forward benchmark of production and experimental lineups."""
import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

from analysis.multiweek_backtest import MODELS, load_history
from analysis.predict_next_week import predict
from analysis.prediction_tracking import DEFAULT_DB, connect, get_prediction, get_snapshot, latest_evaluation_run, parse_time, save_prediction, save_prediction_batch, save_snapshot
from analysis.production_evaluation import _metrics
from data_sources.fixture_validation import validate_week
from data_sources.identity import crosswalk_version, load_crosswalk
from data_sources.tff_official import BASE

STORE = Path('historical_data')
FIXTURE_ENDPOINT = '/api/backend/projection/stats/fixtures?league-id=1'
MODEL_VERSION = 'phase6.1'
POSTPONED = {'POSTPONED', 'PST', 'CANCELLED', 'CANCELED'}
FINISHED = {'FT', 'FINISHED', 'COMPLETED'}
DIRECT_RISK_VERSION = 'phase8.1'


def fetch_official_fixtures():
    """Fetch current official gameweek IDs, deadlines and matches without rewriting an archive."""
    from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError
    if not PROFILE.exists():
        raise TFFFeedError('TFF browser profile is missing; run python -m data_sources.tff_official login')
    with _browser() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE), headless=True)
        try:
            response = ctx.request.get(BASE + FIXTURE_ENDPOINT, timeout=30000)
            if not response.ok:
                raise TFFFeedError(f'Official fixture API HTTP {response.status}')
            payload = response.json()
        finally:
            ctx.close()
    weeks = (payload.get('data') or {}).get('gameweeks') if isinstance(payload, dict) else None
    if not isinstance(weeks, list):
        raise TFFFeedError('Official fixture response has no data.gameweeks list')
    result = {}
    for week in weeks:
        if not isinstance(week, dict) or week.get('order') is None or not isinstance(week.get('matches'), list):
            raise TFFFeedError('Incomplete official gameweek')
        matches = []
        for match in week['matches']:
            if not isinstance(match, dict):
                raise TFFFeedError('Invalid official match')
            matches.append({k:match.get(k) for k in ('id','homeClubId','awayClubId','kickoffAt','homeScore','awayScore','status')})
        key = str(week['order'])
        if key in result:
            raise TFFFeedError('Duplicate official gameweek')
        result[key] = {'gameweek_id':week.get('id'), 'deadline':week.get('deadline'), 'matches':matches}
    return {'classification':'LIVE_API_FIXTURES_NOT_PREDEADLINE_SNAPSHOT',
            'captured_utc':datetime.now(timezone.utc).isoformat(),
            'source_endpoint':FIXTURE_ENDPOINT, 'source_url':BASE+FIXTURE_ENDPOINT,
            'weeks':result}


def next_gameweek(archive, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Current time must include a timezone')
    if archive.get('source_endpoint') != FIXTURE_ENDPOINT:
        raise ValueError('Unrecognized official fixture source')
    weeks = archive.get('weeks') or {}
    for key in sorted(weeks, key=int):
        entry = weeks[key]
        matches = entry.get('matches') or []
        playable = [m for m in matches if str(m.get('status') or '').upper() not in POSTPONED]
        if not playable or any(str(m.get('status') or '').upper() in FINISHED for m in playable):
            continue
        kickoffs = [parse_time(m.get('kickoffAt')) for m in playable]
        if not kickoffs or any(t is None for t in kickoffs):
            continue
        if min(kickoffs) > now:
            return int(key), entry
    raise ValueError('No wholly upcoming gameweek in official fixture data')


def _fixture_lookup(entry):
    lookup = {}
    for match in entry['matches']:
        if str(match.get('status') or '').upper() in POSTPONED:
            continue
        home, away = match.get('homeClubId'), match.get('awayClubId')
        if home is None or away is None or home == away or str(home) in lookup or str(away) in lookup:
            raise ValueError('Missing or duplicate club in selected gameweek')
        lookup[str(home)], lookup[str(away)] = str(away), str(home)
    if not lookup:
        raise ValueError('No playable fixtures')
    return lookup


def generate(*, fixture_archive=None, players=None, records=None, path=DEFAULT_DB,
             now=None, cached=False, strict_pre_deadline=False,
             players_retrieved_at=None):
    """Capture once; run each model on deep copies of that snapshot's inputs."""
    now = now or datetime.now(timezone.utc)
    if fixture_archive is None:
        fixture_archive = fetch_official_fixtures()
    if players is None:
        if cached:
            players = json.loads((STORE/'players.json').read_text(encoding='utf-8'))
        else:
            from data_sources.tff_official import fetch_players
            players = fetch_players()['players']
    if records is None:
        records = load_history()
    week, entry = next_gameweek(fixture_archive, now)
    if strict_pre_deadline:
        deadline=parse_time(entry.get('deadline'))
        retrieved=parse_time(fixture_archive.get('captured_utc'))
        if cached or fixture_archive.get('source_url')!=BASE+FIXTURE_ENDPOINT or \
           deadline is None or retrieved is None or not retrieved<=now<deadline or \
           (now-retrieved).total_seconds()>3600:
            raise ValueError('Fresh official fixture deadline and live player data required before capture')
    quality = validate_week(entry, players)
    fatal = [w for w in quality['warnings'] if w.startswith(('missing_or_duplicate_fixture_id', 'missing_homeClubId',
                                                              'missing_awayClubId', 'self_fixture', 'double_fixtures'))]
    if fatal:
        raise ValueError(f'Unsafe fixture data: {fatal}')
    lookup = _fixture_lookup(entry)
    histories = [{'player_id':p['id'], 'rows':[copy.deepcopy(r) for r in rows if int(r['gameweekOrder']) < week]}
                 for p, rows in records]
    historical_records = [(copy.deepcopy(p), [copy.deepcopy(r) for r in rows if int(r['gameweekOrder']) < week])
                          for p, rows in records]
    archive_time = parse_time(fixture_archive.get('captured_utc'))
    age_hours = (now-archive_time).total_seconds()/3600 if archive_time else None
    warnings = quality['warnings'][:]
    if age_hours is None or age_hours > 24 or age_hours < -1:
        warnings.append('fixture_source_stale_or_undated')
    if cached:
        warnings.append('cached_players_not_live')
    if not entry.get('deadline') or not parse_time(entry['deadline']):
        warnings.append('official_deadline_missing_or_invalid')
    history_by_id = {str(h['player_id']):h['rows'] for h in histories}
    missing_history = sum(not history_by_id.get(str(p['id'])) for p in players)
    quality.update({'warnings':warnings, 'total_tff_players':len(players),
                    'players_without_history':missing_history,
                    'missing_statistics':missing_history,
                    'crosswalk_version':crosswalk_version(load_crosswalk()),
                    'fixture_source_age_hours':round(age_hours,2) if age_hours is not None else None})
    source = {'players':'cached_players_json' if cached else 'official_tff_player_api',
              'players_retrieved_at':players_retrieved_at,
              'capture_kind':'prospective_benchmark' if strict_pre_deadline else 'benchmark',
              'fixtures':fixture_archive.get('source_endpoint'),
              'fixture_source_url':fixture_archive.get('source_url') or BASE+FIXTURE_ENDPOINT,
              'fixtures_retrieved_at':fixture_archive.get('captured_utc'),
              'deadline_source_url':fixture_archive.get('source_url') or BASE+FIXTURE_ENDPOINT,
              'deadline_retrieved_at':fixture_archive.get('captured_utc'),
              'deadline_timezone':'UTC' if str(entry.get('deadline') or '').endswith('Z') else 'offset_in_deadline_value',
              'official_gameweek_id':entry.get('gameweek_id'),
              'histories':'local_player_archives_filtered_before_target_week',
              'deadline_evidence':'official_api_value; local capture timestamp is not independent proof'}
    snapshot = save_snapshot(week, copy.deepcopy(players), copy.deepcopy(entry['matches']), histories,
                             source, deadline_at=entry.get('deadline'),
                             deadline_source=source['deadline_source_url'] if parse_time(entry.get('deadline')) else None,
                             classification='historical_reconstruction' if cached else 'live',
                             data_quality=quality, path=path,
                             require_pre_deadline=strict_pre_deadline)
    fixture_input = {week:lookup}
    from analysis.team_of_week_v36 import load as load_tow
    tow_path = STORE/'team_of_week_verified.json'
    tow = load_tow(tow_path) if tow_path.exists() else {}
    saved = []
    prepared = []
    form_status = {}
    for model in ('short_form_3w', *(name for name in MODELS if name != 'short_form_3w')):
        try:
            result = predict(week, copy.deepcopy(players), copy.deepcopy(historical_records),
                             copy.deepcopy(fixture_input), copy.deepcopy(tow), model=model)
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            if strict_pre_deadline and model != 'short_form_3w':
                form_status[model] = f'not_evaluable: {exc}'
                continue
            raise
        result['benchmark'] = {'variant':'production' if model == 'short_form_3w' else 'experimental_form',
                               'parameters':copy.deepcopy(MODELS[model]), 'fixture_weight':.5,
                               'tow_weight':0.0, 'snapshot_id':snapshot['id']}
        if strict_pre_deadline:
            prepared.append(result)
        else:
            saved.append(save_prediction(snapshot['id'], result, model_version=MODEL_VERSION, path=path))
        form_status[model] = 'saved'
    covariance_status = 'not_evaluable'
    try:
        baseline = predict(week, copy.deepcopy(players), copy.deepcopy(historical_records),
                           copy.deepcopy(fixture_input), copy.deepcopy(tow),
                           experimental_covariance=True, fixture_archive=fixture_archive)
        comparison = baseline['experimental_covariance']['comparison']
        choice = comparison['selected_by_risk_aversion'].get('1.0')
        if choice:
            variant = {'model':'experimental_covariance', 'risk_profile':'experimental_lambda_1',
                       'week':week, 'formation':choice['formation'], 'cost':choice['squad_cost'],
                       'starting_xi':choice['starting_xi'], 'bench':choice['bench'],
                       'captain':choice['captain_name'], 'expected_points':choice['expected_points'],
                       'risk_adjusted_objective':choice['selection_score'],
                       'benchmark':{'variant':'experimental_covariance', 'snapshot_id':snapshot['id'],
                                    'parameters':{'risk_aversion':1.0},
                                    'uncertainty':{'variance':choice['variance'],
                                                   'standard_deviation':choice['standard_deviation'],
                                                   'evidence':baseline['experimental_covariance']['evidence']}}}
            if strict_pre_deadline:
                prepared.append(variant)
            else:
                saved.append(save_prediction(snapshot['id'], variant, model_version=MODEL_VERSION, path=path))
            covariance_status = 'saved'
    except (ValueError, KeyError, TypeError) as exc:
        covariance_status = f'not_evaluable: {exc}'
    if strict_pre_deadline:
        saved = save_prediction_batch(snapshot['id'], prepared, model_version=MODEL_VERSION,
                                      path=path, require_pre_deadline=True)
    return {'gameweek':week, 'gameweek_id':entry.get('gameweek_id'), 'deadline':entry.get('deadline'),
            'snapshot':snapshot, 'predictions':saved, 'data_quality':quality,
            'variants':{'form':form_status, 'covariance':covariance_status,
                        'appearance':'not_evaluable: production xPts already includes playing-time adjustment; separate probability would double-count'}}


def _results_complete(archive, week):
    entry = (archive or {}).get('weeks', {}).get(str(week), {})
    matches = entry.get('matches') or []
    return bool(matches) and all(str(m.get('status') or '').upper() in FINISHED for m in matches)


def _direct_payload(solution, pool, evidence, baseline, snapshot_id, max_mean):
    """Validate one solver result and prepare a complete tracked lineup."""
    from analysis.experimental_covariance import lineup_variance
    from analysis.optimizer import FORMATIONS
    by_id = {p['id']:p for p in pool}
    squad_ids, xi_ids, bench_ids = solution['squad_ids'],solution['starting_xi_ids'],solution['bench_ids']
    if len(squad_ids)!=15 or len(set(squad_ids))!=15 or len(xi_ids)!=11 or len(set(xi_ids))!=11 or len(bench_ids)!=4:
        raise ValueError('Direct-risk solution has invalid squad size')
    if set(xi_ids)|set(bench_ids) != set(squad_ids) or set(xi_ids)&set(bench_ids) or not set(squad_ids)<=set(by_id):
        raise ValueError('Direct-risk solution has missing or duplicate players')
    if solution['captain_id'] not in xi_ids:
        raise ValueError('Direct-risk captain is not in the XI')
    squad = [by_id[i] for i in squad_ids]
    xi = [by_id[i] for i in xi_ids]
    if Counter(p['position'] for p in squad) != {'GK':2,'DEF':5,'MID':5,'FWD':3}:
        raise ValueError('Direct-risk squad violates position counts')
    if max(Counter(str(p['team']) for p in squad).values()) > 3:
        raise ValueError('Direct-risk squad violates club limit')
    counts=Counter(p['position'] for p in xi)
    if counts['GK']!=1 or (counts['DEF'],counts['MID'],counts['FWD']) not in FORMATIONS:
        raise ValueError('Direct-risk XI has invalid formation')
    cost=sum(float(p['price']) for p in squad)
    if cost>100.0001 or abs(cost-solution['squad_cost'])>.01:
        raise ValueError('Direct-risk squad exceeds budget or cost differs')
    raw=sum(float(p['xpts']) for p in xi)+float(by_id[solution['captain_id']]['xpts'])
    if abs(raw-solution['expected_points'])>.01:
        raise ValueError('Direct-risk expected points differ from player scores')
    spread=lineup_variance(xi,solution['captain_id'],evidence)
    if spread is None or abs(spread['standard_deviation']-solution['standard_deviation'])>.01:
        raise ValueError('Direct-risk variance differs from frozen covariance evidence')
    baseline_ids={p['id'] for p in baseline['payload']['starting_xi']}
    swaps={'only_direct':[{'id':i,'name':by_id[i]['name']} for i in sorted(set(xi_ids)-baseline_ids)],
           'only_production':[{'id':i,'name':by_id[i]['name']} for i in sorted(baseline_ids-set(xi_ids))]}
    objective='maximize_expected_points' if solution['mean_floor'] is None else 'minimize_conditional_variance'
    order={'GK':0,'DEF':1,'MID':2,'FWD':3}
    return {'model':'direct_risk_frontier','risk_profile':'experimental_epsilon_constraint',
            'week':10,'formation':solution['formation'],'captain':by_id[solution['captain_id']]['name'],
            'cost':round(cost,2),'budget_remaining':round(100-cost,2),
            'expected_points':round(raw,3),
            'risk_adjusted_objective':-spread['variance'],
            'risk_objective':{'name':'minimize_conditional_variance','estimated_variance':spread['variance'],
                              'sqlite_value':-spread['variance'],'units':'points_squared'},
            'starting_xi':[dict(p,captain=p['id']==solution['captain_id']) for p in sorted(xi,key=lambda p:(order[p['position']],-p['xpts']))],
            'bench':[dict(by_id[i]) for i in bench_ids],
            'benchmark':{'variant':'experimental_direct_risk','snapshot_id':snapshot_id,
                         'parameters':{'mean_floor':solution['mean_floor'],
                                       'mean_floor_fraction':round(solution['mean_floor']/max_mean,6) if solution['mean_floor'] is not None else None,
                                       'objective':objective,'budget':100,'max_per_team':3},
                         'solver':{'status':solution['solver_status'],'proof_status':solution['status'],
                                   'objective':objective,'best_bound':solution['objective_bound'],
                                   'bound_units':'points_squared' if solution['mean_floor'] is not None else 'expected_points'},
                         'uncertainty':{'estimated_variance':spread['variance'],
                                        'standard_deviation':spread['standard_deviation'],
                                        'classification':'conditional_on_appearance',
                                        'completed_match_clusters':evidence['completed_match_clusters']},
                         'swaps_vs_production':swaps,
                         'covariance_evidence_prediction_id':baseline.get('covariance_evidence_prediction_id')}}


def save_direct_risk(*, snapshot_id, path=DEFAULT_DB, time_limit=12):
    """Opt-in: append observed frontier lineups to the original snapshot."""
    from analysis.direct_risk_optimization import compare_saved_gw10, _snapshot_pool
    snapshot=get_snapshot(snapshot_id,path)
    if snapshot is None or snapshot['gameweek']!=10:
        raise ValueError('Original GW10 snapshot required')
    analysis=compare_saved_gw10(snapshot_id=snapshot_id,time_limit=time_limit,path=path)
    pool,_=_snapshot_pool(snapshot,10)
    with connect(path) as db:
        rows=[r[0] for r in db.execute('SELECT id FROM predictions WHERE snapshot_id=?',(snapshot_id,))]
    predictions=[get_prediction(pid,path) for pid in rows]
    baseline=next((p for p in predictions if p['model']=='short_form_3w' and
                   p['payload'].get('benchmark',{}).get('variant')=='production'),None)
    covariance=next((p for p in predictions if p['model']=='experimental_covariance'),None)
    if baseline is None or covariance is None:
        raise ValueError('Original production and covariance records required')
    evidence=covariance['payload']['benchmark']['uncertainty']['evidence']
    baseline={**baseline,'covariance_evidence_prediction_id':covariance['id']}
    frontier=analysis['direct']['observed_frontier']
    prepared=[_direct_payload(solution,pool,evidence,baseline,snapshot_id,
                              analysis['direct']['max_mean']['expected_points']) for solution in frontier]
    saved=[save_prediction(snapshot_id,payload,model_version=DIRECT_RISK_VERSION,path=path) for payload in prepared]
    return {'snapshot_id':snapshot_id,'gameweek':10,'classification':'experimental_conditional_on_appearance',
            'saved':saved,'solver_statuses':[p['benchmark']['solver']['status'] for p in prepared],
            'limitations':analysis['limitations']}


def report(path=DEFAULT_DB, store=STORE):
    path = Path(path)
    if not path.exists():
        return {'predictions':[], 'risk_return':[], 'evaluation_runs':[], 'by_gameweek':{}, 'by_model':{},
                'counts':{'verified':0,'unverified':0,'locally_recorded_pre_deadline':0,
                          'post_deadline':0,'complete_evaluations':0}}
    with connect(path) as db:
        ids = [r[0] for r in db.execute('SELECT id FROM predictions ORDER BY created_at,id')]
    predictions=[get_prediction(pid,path) for pid in ids]
    benchmark_predictions=[p for p in predictions if 'benchmark' in p['payload']]
    latest_by_snapshot={sid:latest_evaluation_run(sid,path)
                        for sid in {p['snapshot_id'] for p in benchmark_predictions}}
    from analysis.benchmark_verification import provenance
    rows = []
    for prediction in benchmark_predictions:
        pid=prediction['id']
        snapshot = get_snapshot(prediction['snapshot_id'], path)
        run=latest_by_snapshot[prediction['snapshot_id']]
        evaluation=run['payload']['prediction_results'].get(pid) if run else None
        if evaluation is None:
            evaluation={'status':'not_evaluable',
                        'reason':'not_in_latest_evaluation_run' if run else 'evaluation_not_started'}
        evidence=provenance(prediction,snapshot)
        rows.append({'id':pid, 'snapshot_id':prediction['snapshot_id'],
                     'gameweek':prediction['gameweek'], 'model':prediction['model'],
                     'model_version':prediction['model_version'], 'created_at':prediction['created_at'],
                     'verification_status':evidence['status'],
                     'stored_verification_status':prediction['status'],
                     'provenance':evidence,
                     'expected_points':prediction['raw_expected_points'],
                     'formation':prediction['payload'].get('formation'),
                     'captain':prediction['payload'].get('captain'),
                     'starting_xi':prediction['payload']['starting_xi'],
                     'bench':prediction['payload']['bench'],
                     'parameters':prediction['payload']['benchmark'].get('parameters'),
                     'uncertainty':prediction['payload']['benchmark'].get('uncertainty'),
                     'solver':prediction['payload']['benchmark'].get('solver'),
                     'swaps_vs_production':prediction['payload']['benchmark'].get('swaps_vs_production'),
                     'risk_objective':prediction['payload'].get('risk_objective'),
                     'risk_adjusted_objective':prediction['risk_adjusted_objective'],
                     'source':snapshot['source'], 'data_quality':snapshot['payload'].get('data_quality'),
                     'evaluation':evaluation,
                     'actuals_source':run['source'].get('actuals_url_template') if run and evaluation['status']=='complete' else None})
    from analysis.experimental_covariance import lineup_variance
    evidence_by_snapshot={p['snapshot_id']:p['payload']['benchmark']['uncertainty']['evidence']
                          for p in benchmark_predictions if p['model']=='experimental_covariance' and
                          p['payload'].get('benchmark',{}).get('uncertainty',{}).get('evidence')}
    risk_return=[]
    for row in rows:
        evidence=evidence_by_snapshot.get(row['snapshot_id'])
        captain=next((p for p in row['starting_xi'] if p.get('captain')),None)
        spread=lineup_variance(row['starting_xi'],captain['id'],evidence) if evidence and captain else None
        row['estimated_standard_deviation']=spread['standard_deviation'] if spread else None
        if spread:
            risk_return.append({'prediction_id':row['id'],'snapshot_id':row['snapshot_id'],
                                'gameweek':row['gameweek'],'model':row['model'],
                                'expected_points':row['expected_points'],
                                'estimated_standard_deviation':spread['standard_deviation'],
                                'mean_floor':(row['parameters'] or {}).get('mean_floor'),
                                'solver_status':(row['solver'] or {}).get('status')})
    def groups(key):
        output = {}
        for group in sorted({str(row[key]) for row in rows}):
            subset = [r for r in rows if str(r[key]) == group]
            complete = [r['evaluation'] for r in subset if r['evaluation']['status']=='complete']
            output[group] = {'n':len(subset), 'evaluable':len(complete),
                             'team_metrics':_metrics([r['error'] for r in complete]),
                             'player_metrics':_metrics([p['error'] for r in complete for p in r['players']]),
                             'recent_3_baseline':_metrics([r['actual_points']-r['baselines']['recent_3_baseline']
                                                           for r in complete if r['baselines']['recent_3_baseline'] is not None]),
                             'season_to_date_baseline':_metrics([r['actual_points']-r['baselines']['season_to_date_baseline']
                                                                  for r in complete if r['baselines']['season_to_date_baseline'] is not None])}
        return output
    verified = sum(r['verification_status']=='verified_pre_deadline' for r in rows)
    evaluation_runs=[{'id':run['id'],'snapshot_id':sid,'status':run['status'],
                      'created_at':run['created_at'],'source':run['source'],
                      'complete_predictions':run['payload']['complete_predictions'],
                      'total_predictions':run['payload']['total_predictions'],
                      'fixture_issues':run['payload']['fixture_issues'],
                      'player_issues':run['payload']['player_issues']}
                     for sid,run in latest_by_snapshot.items() if run]
    return {'predictions':rows, 'risk_return':risk_return,
            'by_gameweek':groups('gameweek'), 'by_model':groups('model'),
            'evaluation_runs':evaluation_runs,
            'counts':{'verified':verified, 'unverified':len(rows)-verified,
                      'locally_recorded_pre_deadline':sum(r['verification_status']=='locally_recorded_pre_deadline_not_verified' for r in rows),
                      'post_deadline':sum(r['verification_status']=='post_deadline' for r in rows),
                      'complete_evaluations':sum(r['evaluation']['status']=='complete' for r in rows)},
            'limitations':['Local timestamps and an official API deadline do not independently prove pre-deadline capture.',
                           'Evaluation requires matching completed official fixtures and validated TFF player-history rows.',
                           'Appearance variant withheld because production xPts already discounts minutes.',
                           'Compare models only across genuine out-of-sample weeks with complete actual results.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cached', action='store_true', help='Explicit retrospective diagnostic using cached player data')
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--evaluate-snapshot', help='Fetch official results and persist an idempotent evaluation run')
    parser.add_argument('--direct-risk-snapshot', help='Opt in: append direct-risk frontier predictions to an existing GW10 snapshot')
    args = parser.parse_args()
    if args.evaluate_snapshot:
        from analysis.benchmark_evaluation import evaluate_gameweek
        result=evaluate_gameweek(args.evaluate_snapshot)
    else:
        result=(save_direct_risk(snapshot_id=args.direct_risk_snapshot) if args.direct_risk_snapshot else
                report() if args.report else generate(cached=args.cached))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
