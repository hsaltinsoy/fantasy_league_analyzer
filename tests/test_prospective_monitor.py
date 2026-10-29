import copy
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from analysis import live_benchmark, prospective_monitor as monitor
from analysis.benchmark_evaluation import PLAYER_HISTORY_URL
from analysis.prediction_tracking import (get_prediction, get_snapshot,
    latest_evaluation_run, save_prediction, save_prediction_batch, save_snapshot)
from data_sources.tff_official import BASE


NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def fixture_archive(status='SCHEDULED', *, deadline='2026-10-30T16:00:00Z'):
    return {'source_endpoint':live_benchmark.FIXTURE_ENDPOINT,
            'source_url':BASE+live_benchmark.FIXTURE_ENDPOINT,
            'captured_utc':NOW.isoformat(),
            'weeks':{'10':{'gameweek_id':10,'deadline':deadline,
                'matches':[{'id':100,'homeClubId':1,'awayClubId':2,
                            'kickoffAt':'2026-10-30T17:00:00Z','status':status,
                            'homeScore':1 if status=='FT' else None,
                            'awayScore':0 if status=='FT' else None}]}}}


def test_capture_is_idempotent_and_reuses_one_official_snapshot(tmp_path, monkeypatch):
    path=tmp_path/'tracking.sqlite3'
    created=[]
    monkeypatch.setattr(monitor,'_existing_for_week',lambda *args: created[0] if created else None)
    monkeypatch.setattr(monitor,'_benchmark_snapshots',lambda *args: [])
    def fake_generate(**kwargs):
        assert kwargs['strict_pre_deadline'] is True
        assert kwargs['fixture_archive']['weeks']['10']['gameweek_id']==10
        created.append({'id':'one-snapshot','deadline':'2026-10-30T16:00:00Z'})
        return {'snapshot':{'id':'one-snapshot'},'predictions':[{'id':'prediction'}],
                'variants':{},'data_quality':{}}
    monkeypatch.setattr(monitor.live_benchmark,'generate',fake_generate)
    first=monitor.capture(path=path,fixture_archive=fixture_archive(),now=NOW,
                          players_provider=lambda:{'players':[{'id':1}]},records_provider=lambda:[])
    second=monitor.capture(path=path,fixture_archive=fixture_archive(),now=NOW,
                           players_provider=lambda:pytest.fail('Repeat must not fetch players'))
    assert first['status']=='captured' and second['status']=='already_captured'
    assert first['snapshot_id']==second['snapshot_id']=='one-snapshot'
    assert len(created)==1


def test_capture_reads_clock_after_fresh_fixture_fetch(tmp_path, monkeypatch):
    fresh = datetime.now(timezone.utc)
    archive = fixture_archive()
    archive['captured_utc'] = fresh.isoformat()
    archive['weeks']['10']['deadline'] = (fresh+timedelta(days=1)).isoformat()
    archive['weeks']['10']['matches'][0]['kickoffAt'] = (fresh+timedelta(days=1,hours=1)).isoformat()
    monkeypatch.setattr(monitor.live_benchmark,'fetch_official_fixtures',lambda:archive)
    monkeypatch.setattr(monitor.live_benchmark,'generate',lambda **kwargs:{
        'snapshot':{'id':'fresh'},'predictions':[],'variants':{},'data_quality':{}})
    assert monitor.capture(path=tmp_path/'tracking.sqlite3',
        players_provider=lambda:{'players':[{'id':1}]},records_provider=lambda:[])['status']=='captured'


def test_deadline_unknown_or_passed_and_bad_source_fail_before_players(tmp_path):
    for archive in (fixture_archive(deadline=None), fixture_archive(deadline='2026-10-28T16:00:00Z')):
        with pytest.raises(ValueError,match='deadline'):
            monitor.capture(path=tmp_path/'absent.sqlite3',fixture_archive=archive,now=NOW,
                            players_provider=lambda:pytest.fail('No player fetch after deadline'))
    bad=fixture_archive()
    bad['source_url']='https://example.invalid/fixtures'
    with pytest.raises(ValueError,match='official'):
        monitor.capture(path=tmp_path/'absent.sqlite3',fixture_archive=bad,now=NOW)
    assert not (tmp_path/'absent.sqlite3').exists()


def _saved_benchmark(path):
    players=[{'id':i,'name':f'P{i}','club_id':1,'position':'MID','price':4} for i in range(1,16)]
    source={'capture_kind':'prospective_benchmark','official_gameweek_id':10,
            'fixture_source_url':BASE+live_benchmark.FIXTURE_ENDPOINT,
            'deadline_source_url':BASE+live_benchmark.FIXTURE_ENDPOINT,
            'deadline_retrieved_at':NOW.isoformat(),
            'fixtures_retrieved_at':NOW.isoformat()}
    fixture=fixture_archive()['weeks']['10']['matches']
    snapshot=save_snapshot(10,players,fixture,[],source,deadline_at='2026-10-30T16:00:00Z',
                           deadline_source=BASE+live_benchmark.FIXTURE_ENDPOINT,path=path)
    xi=[{'id':i,'name':f'P{i}','position':'MID','price':4,'team':'1','opponent':'2',
         'xpts':float(i),'captain':i==1} for i in range(1,12)]
    payload={'week':10,'model':'short_form_3w','risk_profile':'balanced','starting_xi':xi,
             'bench':[{'id':i} for i in range(12,16)],'benchmark':{'snapshot_id':snapshot['id']}}
    prediction=save_prediction(snapshot['id'],payload,path=path)
    return snapshot,prediction


def test_incomplete_fixtures_do_not_create_evaluation_run(tmp_path):
    path=tmp_path/'tracking.sqlite3'
    snapshot,_=_saved_benchmark(path)
    result=monitor.evaluate(gameweek=10,path=path,fixture_archive=fixture_archive())
    assert result['status']=='not_ready'
    assert result['evaluation_run_created'] is False
    assert latest_evaluation_run(snapshot['id'],path) is None


def test_complete_official_results_are_idempotent_and_ranked_within_xi(tmp_path):
    path=tmp_path/'tracking.sqlite3'
    snapshot,prediction=_saved_benchmark(path)
    original=get_prediction(prediction['id'],path)
    archive=fixture_archive('FT')
    def rows_provider(week, ids):
        assert week==10 and len(ids)==11
        return {'source_url':PLAYER_HISTORY_URL,'retrieved_at':NOW.isoformat(),
                'rows_by_player':{str(pid):[{'gameweekOrder':10,'gameweekId':10,
                    'opponentClubId':2,'homeAway':'H','points':float(pid)}] for pid in ids}}
    first=monitor.evaluate(gameweek=10,path=path,fixture_archive=archive,rows_provider=rows_provider)
    second=monitor.evaluate(gameweek=10,path=path,fixture_archive=archive,rows_provider=rows_provider)
    assert first['status']==second['status']=='complete'
    assert first['evaluation_run_id']==second['evaluation_run_id']
    assert first['evaluation_run_created'] and not second['evaluation_run_created']
    assert get_prediction(prediction['id'],path)==original
    assert get_snapshot(snapshot['id'],path)['id']==snapshot['id']
    run=latest_evaluation_run(snapshot['id'],path)
    rank=run['payload']['prediction_results'][prediction['id']]['xi_ranking']
    assert rank['population']=='selected_starting_xi_only'
    assert rank['spearman']==1
    assert rank['precision_at_20'] is None
    summary=monitor.report(path)
    assert summary['by_model']['short_form_3w']['complete']==1
    assert summary['predictions'][0]['independently_verified'] is False


def test_dashboard_and_report_api_show_missing_prospective_data_safely():
    from app import create_app
    client=create_app().test_client()
    page=client.get('/')
    assert page.status_code==200
    assert b'Prospective model monitoring' in page.data
    response=client.get('/api/prospective/report')
    assert response.status_code==200
    assert response.json['classification']=='prospective_local_timestamp_not_independent_proof'


def test_phase15_variants_use_one_saved_snapshot_and_training_parameters(monkeypatch):
    from analysis import experimental_prospective as experiment
    snapshot_id='shared-snapshot'
    players=[]
    for position,count in (('GK',2),('DEF',5),('MID',5),('FWD',3)):
        players.extend({'id':len(players)+1,'name':f'P{len(players)+1}',
                        'position':position,'price':4,'club_id':1} for _ in range(count))
    histories=[{'player_id':p['id'],'rows':[{'gameweekOrder':week,'points':2,
        'minutesPlayed':90,'goals':0,'assists':0} for week in range(1,10)]} for p in players]
    snapshot={'id':snapshot_id,'gameweek':10,'classification':'live',
              'payload':{'players':players,'histories':histories,
                  'fixtures':fixture_archive()['weeks']['10']['matches']}}
    monkeypatch.setattr(experiment,'get_snapshot',lambda *args: snapshot)
    monkeypatch.setattr(experiment,'train_for_target',lambda *args,**kwargs: (
        {'coefficients':[1.0]+[0.0]*len(experiment.FEATURES),
         'centers':{key:0.0 for key in experiment.FEATURES},
         'scales':{key:1.0 for key in experiment.FEATURES},'training_n':200,'alpha':100},
        {'training_weeks':[4,5,6,7,8],'training_n':200}))
    monkeypatch.setattr(experiment,'build_candidate_pool',lambda *args:(
        [dict(p,team='1',opponent='2',xpts=2.0) for p in players],{}))
    def fake_optimize(candidates, risk_profile):
        assert risk_profile=='balanced'
        return {'starting_xi':candidates[:11],'squad':candidates,
                'captain':candidates[0],'formation':'4-4-2','squad_cost':60,
                'expected_points':12,'risk_adjusted_objective':12,'status':'optimal'}
    monkeypatch.setattr(experiment,'optimize',fake_optimize)
    saved=[]
    def fake_save(sid,results,**kwargs):
        assert sid==snapshot_id and kwargs['require_pre_deadline'] is True
        saved.extend(copy.deepcopy(results))
        return [{'id':str(i)} for i in range(len(results))]
    monkeypatch.setattr(experiment,'save_prediction_batch',fake_save)
    result=experiment.save_variants(snapshot_id,path='unused.sqlite3')
    assert result['status']=='saved' and len(saved)==2
    assert {item['benchmark']['snapshot_id'] for item in saved}=={snapshot_id}
    assert {item['benchmark']['parameters']['training']['training_n'] for item in saved}=={200}
    assert saved[0]['model']!=saved[1]['model']


def test_phase15_prospective_fit_excludes_last_and_target_week(tmp_path, monkeypatch):
    from analysis import experimental_prospective as experiment
    import analysis.recovered_model_evaluation as recovered_model
    (tmp_path/'coverage_report.json').write_text('{}', encoding='utf-8')
    records={str(i):[{'gameweekOrder':week,'points':1,'minutesPlayed':90,
                       'goals':0,'assists':0} for week in range(1,10)]
             for i in range(1,121)}
    monkeypatch.setattr(experiment,'_load_inputs',lambda *_: ({},{},{},records))
    monkeypatch.setattr(experiment,'_week_samples',lambda week,*_: {
        'all':[{'player_id':str(i),'actual':float(week)} for i in range(1,121)]})
    monkeypatch.setattr(recovered_model,'_positions_for_week',lambda *args: (
        {str(i):{'position':'MID'} for i in range(1,121)},[]))
    seen=[]
    monkeypatch.setattr(experiment,'fit_ridge',lambda rows: seen.append(rows) or {'trained':True})
    _, training=experiment.train_for_target(10,store=tmp_path,recovered=tmp_path)
    assert training['training_weeks']==[4,5,6,7,8]
    assert training['training_n']==600
    assert len(seen[0])==600


def test_atomic_batch_rolls_back_invalid_model_and_rejects_late_insert(tmp_path, monkeypatch):
    path=tmp_path/'tracking.sqlite3'
    url=BASE+live_benchmark.FIXTURE_ENDPOINT
    snapshot=save_snapshot(20,[{'id':i} for i in range(1,16)],[],[],{},
        deadline_at='2099-01-02T12:00:00Z',deadline_source=url,path=path,
        require_pre_deadline=True)
    valid={'week':20,'model':'short_form_3w','risk_profile':'balanced',
           'starting_xi':[{'id':i,'xpts':2,'captain':i==1} for i in range(1,12)],
           'bench':[{'id':i} for i in range(12,16)]}
    invalid={**valid,'model':'broken','bench':[]}
    monkeypatch.setattr('analysis.prediction_tracking.utc_now',lambda:'2099-01-01T12:00:00+00:00')
    with pytest.raises(ValueError,match='complete XI'):
        save_prediction_batch(snapshot['id'],[valid,invalid],path=path,require_pre_deadline=True)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM predictions').fetchone()[0]==0
    monkeypatch.setattr('analysis.prediction_tracking.utc_now',lambda:'2099-01-03T12:00:00+00:00')
    with pytest.raises(ValueError,match='deadline'):
        save_prediction_batch(snapshot['id'],[valid],path=path,require_pre_deadline=True)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM predictions').fetchone()[0]==0


def test_real_capture_flow_shares_snapshot_and_never_duplicates(tmp_path, monkeypatch):
    path=tmp_path/'tracking.sqlite3'
    archive=fixture_archive()
    players=[{'id':i,'name':f'P{i}','position':'MID','club_id':1,'price':4}
             for i in range(1,16)]
    records=[(p,[{'gameweekOrder':9,'points':2,'minutesPlayed':90}]) for p in players]
    monkeypatch.setattr(live_benchmark,'load_crosswalk',lambda:{})
    monkeypatch.setattr(live_benchmark,'crosswalk_version',lambda _: 'test')
    monkeypatch.setattr('analysis.team_of_week_v36.load',lambda _: {})
    monkeypatch.setattr('analysis.prediction_tracking.utc_now',lambda:NOW.isoformat())
    def fake_predict(week,input_players,input_records,fixtures,tow,model='short_form_3w',**kwargs):
        if kwargs.get('experimental_covariance'):
            raise ValueError('No covariance clusters')
        return {'week':week,'model':model,'risk_profile':'balanced',
                'starting_xi':[dict(p,team='1',opponent='2',xpts=2.0,
                                    captain=p['id']==1) for p in input_players[:11]],
                'bench':input_players[11:],'formation':'4-4-2'}
    monkeypatch.setattr(live_benchmark,'predict',fake_predict)
    first=monitor.capture(path=path,fixture_archive=archive,now=NOW,
                          players_provider=lambda:{'players':players},records_provider=lambda:records)
    second=monitor.capture(path=path,fixture_archive=archive,now=NOW,
                           players_provider=lambda:pytest.fail('repeat fetched players'))
    assert first['status']=='captured' and first['predictions_created']==5
    assert second['status']=='already_captured' and second['snapshot_id']==first['snapshot_id']
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM snapshots').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM predictions').fetchone()[0]==5
    snapshot=get_snapshot(first['snapshot_id'],path)
    assert snapshot['source']['capture_kind']=='prospective_benchmark'
    assert snapshot['source']['official_gameweek_id']==10
    assert all(get_prediction(pid,path)['snapshot_id']==snapshot['id'] for pid in first['model_ids'])
