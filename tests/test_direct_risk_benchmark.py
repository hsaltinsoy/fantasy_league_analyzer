import copy
import math
import sqlite3

import pytest

from analysis import live_benchmark
from analysis.prediction_tracking import connect, get_prediction, get_snapshot, save_prediction, save_snapshot
from app.benchmark_view import risk_chart_view


def saved_fixture(tmp_path):
    path=tmp_path/'tracking.sqlite3'
    positions=['GK','GK']+['DEF']*5+['MID']*5+['FWD']*3
    players=[{'id':i+1,'name':f'Player {i+1}','club_id':1 if i%2 else 2,
              'team':str(1 if i%2 else 2),'position':pos,'price':5.,'xpts':4.,
              'opponent':str(2 if i%2 else 1)} for i,pos in enumerate(positions)]
    # Three completed fixtures cover the six clubs represented in the squad.
    for i,p in enumerate(players):
        club=i%6+1
        p['team']=str(club)
        p['club_id']=club
        p['opponent']=str(club+1 if club%2 else club-1)
    xi_ids=[1,3,4,5,6,8,9,10,11,13,14]
    xi=[dict(p,captain=p['id']==13) for p in players if p['id'] in xi_ids]
    bench=[dict(p) for p in players if p['id'] not in xi_ids]
    matches=[{'id':i,'homeClubId':i*2-1,'awayClubId':i*2,'status':'SCHEDULED',
              'homeScore':None,'awayScore':None} for i in range(1,4)]
    snapshot=save_snapshot(10,players,matches,[{'player_id':p['id'],'rows':[{'gameweekOrder':9,'points':2}]}
                                         for p in players],
                           {'fixtures':'official_test'},deadline_at='2026-10-30T16:00:00Z',
                           path=path)
    evidence={'player_variance':{str(p['id']):{'variance':1.} for p in players},
              'position_variance':{},'completed_match_clusters':81,
              'covariance':{kind:{'shrunk':None} for kind in ('def_def','gk_def','opposing_def_att')}}
    baseline={'model':'short_form_3w','risk_profile':'balanced','formation':'4-4-2',
              'cost':75.,'starting_xi':xi,'bench':bench,'captain':'Player 13',
              'benchmark':{'variant':'production','parameters':{}}}
    first=save_prediction(snapshot['id'],baseline,path=path)
    covariance={**copy.deepcopy(baseline),'model':'experimental_covariance',
                'benchmark':{'variant':'experimental_covariance','uncertainty':{'evidence':evidence}}}
    second=save_prediction(snapshot['id'],covariance,path=path)
    solution={'status':'feasible','solver_status':'FEASIBLE','objective_bound':10.,
              'mean_floor':47.,'formation':'4-4-2','squad_ids':list(range(1,16)),
              'starting_xi_ids':xi_ids,'bench_ids':[2,7,12,15],
              'captain_id':13,'captain_name':'Player 13','squad_cost':75.,
              'expected_points':48.,'variance':14.,'standard_deviation':round(math.sqrt(14),4)}
    return path,snapshot,players,first,second,solution


def official_evidence(snapshot, players, path, *, points=2.):
    from analysis.benchmark_evaluation import FIXTURE_URL, PLAYER_HISTORY_URL
    matches=copy.deepcopy(get_snapshot(snapshot['id'],path)['payload']['fixtures'])
    for match in matches:
        match.update(status='FT',homeScore=1,awayScore=0)
    archive={'source_url':FIXTURE_URL,'captured_utc':'2026-10-31T12:00:00Z',
             'weeks':{'10':{'gameweek_id':10,'matches':matches}}}
    by_id={str(p['id']):p for p in players}
    def fetched(week,ids):
        return {'source_url':PLAYER_HISTORY_URL,'retrieved_at':'2026-10-31T12:00:00Z',
                'rows_by_player':{str(i):[{'gameweekId':10,'gameweekOrder':10,'points':points,
                                         'opponentClubId':int(by_id[str(i)]['opponent']),
                                         'homeAway':'H' if by_id[str(i)]['club_id']%2 else 'A'}]
                                  for i in ids}}
    return archive,fetched


def test_direct_append_reuses_snapshot_and_preserves_records(tmp_path,monkeypatch):
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    original=[get_prediction(pid,path) for pid in (first['id'],second['id'])]
    monkeypatch.setattr('analysis.direct_risk_optimization.compare_saved_gw10',lambda **kwargs:
                        {'direct':{'observed_frontier':[solution],
                                   'max_mean':{'expected_points':48.}},'limitations':[]})
    monkeypatch.setattr('analysis.direct_risk_optimization._snapshot_pool',lambda *_:(players,{}))
    result=live_benchmark.save_direct_risk(snapshot_id=snapshot['id'],path=path,time_limit=1)
    assert len(result['saved'])==1
    item=get_prediction(result['saved'][0]['id'],path)
    assert item['snapshot_id']==snapshot['id']
    assert item['id'] not in (first['id'],second['id'])
    assert item['raw_expected_points']==48.
    assert item['risk_adjusted_objective']==-14.
    assert item['payload']['benchmark']['parameters']['mean_floor']==47.
    assert item['payload']['benchmark']['solver']=={
        'status':'FEASIBLE','proof_status':'feasible','objective':'minimize_conditional_variance',
        'best_bound':10.,'bound_units':'points_squared'}
    assert len(item['payload']['starting_xi'])==11 and len(item['payload']['bench'])==4
    assert [get_prediction(pid,path) for pid in (first['id'],second['id'])]==original
    assert get_snapshot(snapshot['id'],path)['id']==snapshot['id']
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]==3
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('UPDATE predictions SET model=? WHERE id=?',('changed',item['id']))


def test_direct_payload_rejects_constraint_and_score_errors(tmp_path):
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    evidence=get_prediction(second['id'],path)['payload']['benchmark']['uncertainty']['evidence']
    baseline=get_prediction(first['id'],path)
    with pytest.raises(ValueError,match='expected points'):
        live_benchmark._direct_payload({**solution,'expected_points':99.},players,evidence,baseline,snapshot['id'],48.)
    with pytest.raises(ValueError,match='budget or cost'):
        live_benchmark._direct_payload({**solution,'squad_cost':101.},players,evidence,baseline,snapshot['id'],48.)
    with pytest.raises(ValueError,match='captain'):
        live_benchmark._direct_payload({**solution,'captain_id':15},players,evidence,baseline,snapshot['id'],48.)


def test_completed_report_scores_all_models_from_one_actual_provider(tmp_path):
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    from analysis.benchmark_evaluation import evaluate_gameweek, PLAYER_HISTORY_URL
    calls=[]
    archive,fetched=official_evidence(snapshot,players,path)
    def official(week,ids):
        calls.append((week,set(ids)))
        return fetched(week,ids)
    run=evaluate_gameweek(snapshot['id'],fixture_archive=archive,rows_provider=official,path=path)
    result=live_benchmark.report(path=path)
    assert run['status']=='complete'
    assert len(calls)==1 and calls[0][0]==10
    assert len(result['predictions'])==2
    assert all(row['evaluation']['actual_points']==24. for row in result['predictions'])
    assert all(row['evaluation']['starting_xi_actual_points']==22. for row in result['predictions'])
    assert all(row['evaluation']['captain_contribution']==2. for row in result['predictions'])
    assert result['by_model']['short_form_3w']['team_metrics']['mae']==24.
    assert result['by_model']['short_form_3w']['team_metrics']['rmse']==24.
    assert result['by_model']['short_form_3w']['player_metrics']['mae']==2.
    assert all(row['actuals_source']==PLAYER_HISTORY_URL for row in result['predictions'])
    assert len(result['risk_return'])==2
    chart=risk_chart_view(result,snapshot['id'],(first['id'],))
    assert len(chart['points'])==2 and chart['points'][0]['selected']


def test_deadline_unknown_snapshot_new_postdeadline_prediction_is_not_predeadline(tmp_path,monkeypatch):
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    monkeypatch.setattr('analysis.prediction_tracking.utc_now',lambda:'2026-10-31T12:00:00+00:00')
    payload=get_prediction(first['id'],path)['payload']
    saved=save_prediction(snapshot['id'],payload,path=path)
    assert saved['status']=='post_deadline'


def test_direct_risk_endpoint_is_explicit_opt_in(monkeypatch):
    calls=[]
    monkeypatch.setattr(live_benchmark,'save_direct_risk',lambda **kwargs:
                        calls.append(kwargs) or {'saved':[],'snapshot_id':kwargs['snapshot_id']})
    from app import create_app
    client=create_app().test_client()
    assert client.post('/api/benchmark/direct-risk',json={}).status_code==400
    assert calls==[]
    response=client.post('/api/benchmark/direct-risk',json={'snapshot_id':'original'})
    assert response.status_code==200
    assert calls==[{'snapshot_id':'original'}]


def test_incomplete_fixtures_are_idempotent_and_skip_player_fetch(tmp_path):
    from analysis.benchmark_evaluation import evaluate_gameweek
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    archive,_=official_evidence(snapshot,players,path)
    archive['weeks']['10']['matches'][0]['status']='SCHEDULED'
    def forbidden(*_):
        raise AssertionError('Player rows must not be fetched before every official match finishes')
    a=evaluate_gameweek(snapshot['id'],fixture_archive=archive,rows_provider=forbidden,path=path)
    b=evaluate_gameweek(snapshot['id'],fixture_archive=archive,rows_provider=forbidden,path=path)
    assert a['id']==b['id'] and a['status']=='incomplete'
    assert a['payload']['fixture_issues']==['official_fixtures_incomplete']
    assert a['payload']['complete_predictions']==0
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM evaluation_runs').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]==2
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('UPDATE evaluation_runs SET status=? WHERE id=?',('complete',a['id']))


def test_fixture_identity_and_gameweek_id_are_required(tmp_path):
    from analysis.benchmark_evaluation import evaluate_gameweek
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    archive,_=official_evidence(snapshot,players,path)
    archive['weeks']['10']['matches'][0]['id']=999
    run=evaluate_gameweek(snapshot['id'],fixture_archive=archive,path=path)
    assert run['status']=='incomplete'
    assert run['payload']['fixture_issues']==['fixture_id_or_club_mismatch']
    archive['weeks']['10']['matches'][0]['id']=1
    archive['weeks']['10']['gameweek_id']=None
    run=evaluate_gameweek(snapshot['id'],fixture_archive=archive,path=path)
    assert run['payload']['fixture_issues']==['missing_official_gameweek_id']


@pytest.mark.parametrize('problem,expected',[
    ('missing','missing_or_duplicate_gameweek_result'),
    ('duplicate','missing_or_duplicate_gameweek_result'),
    ('wrong_week','gameweek_id_or_order_mismatch'),
    ('wrong_opponent','opponent_or_venue_mismatch'),
    ('invalid_points','missing_or_invalid_points'),
])
def test_inconsistent_actual_rows_make_affected_predictions_incomplete(tmp_path,problem,expected):
    from analysis.benchmark_evaluation import evaluate_gameweek
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    archive,valid=official_evidence(snapshot,players,path)
    def broken(week,ids):
        data=valid(week,ids)
        rows=data['rows_by_player']
        if problem=='missing': rows.pop('1')
        elif problem=='duplicate': rows['1'].append(copy.deepcopy(rows['1'][0]))
        elif problem=='wrong_week': rows['1'][0]['gameweekId']=11
        elif problem=='wrong_opponent': rows['1'][0]['opponentClubId']=999
        elif problem=='invalid_points': rows['1'][0]['points']=None
        return data
    run=evaluate_gameweek(snapshot['id'],fixture_archive=archive,rows_provider=broken,path=path)
    assert run['status']=='incomplete'
    assert run['payload']['player_issues']['1']==expected
    assert all(row['status']=='incomplete' for row in run['payload']['prediction_results'].values())
    assert run['payload']['complete_predictions']==0


def test_explicit_zero_is_scored_and_duplicate_complete_run_is_reused(tmp_path):
    from analysis.benchmark_evaluation import evaluate_gameweek
    path,snapshot,players,first,second,solution=saved_fixture(tmp_path)
    archive,zero=official_evidence(snapshot,players,path,points=0.)
    a=evaluate_gameweek(snapshot['id'],fixture_archive=archive,rows_provider=zero,path=path)
    b=evaluate_gameweek(snapshot['id'],fixture_archive=archive,rows_provider=zero,path=path)
    assert a['id']==b['id'] and a['status']=='complete'
    reversed_archive=copy.deepcopy(archive)
    reversed_archive['weeks']['10']['matches'].reverse()
    reordered=evaluate_gameweek(snapshot['id'],fixture_archive=reversed_archive,rows_provider=zero,path=path)
    assert reordered['id']==a['id']
    assert all(row['actual_points']==0 for row in a['payload']['prediction_results'].values())
    _,corrected=official_evidence(snapshot,players,path,points=1.)
    c=evaluate_gameweek(snapshot['id'],fixture_archive=archive,rows_provider=corrected,path=path)
    assert c['id']!=a['id'] and c['status']=='complete'
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM evaluation_runs').fetchone()[0]==2
        assert db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]==2
