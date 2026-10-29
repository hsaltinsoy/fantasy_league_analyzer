import sqlite3

import pytest

from analysis.prediction_tracking import (
    connect, evaluate_prediction, get_prediction, get_snapshot, save_prediction, save_snapshot, verification,
)


def test_verification_requires_sourced_aware_deadline():
    before='2026-10-29T10:00:00Z'
    deadline='2026-10-29T11:00:00Z'
    official='https://tfffantezilig.com/api/backend/projection/stats/fixtures?league-id=1'
    assert verification(before,deadline,official)=='locally_recorded_pre_deadline_not_verified'
    assert verification(before,deadline,'official fixture')=='deadline_unknown'
    assert verification(deadline,deadline,official)=='post_deadline'
    assert verification(before,deadline,None)=='deadline_unknown'
    assert verification(before,None,'official fixture')=='deadline_unknown'
    assert verification(before,deadline,'official fixture','historical_reconstruction')=='historical_reconstruction_not_verified'
    with pytest.raises(ValueError): verification('2026-10-29T10:00:00',deadline,'official fixture')


def test_predictions_are_append_only_and_evaluate_raw_points(tmp_path):
    path=tmp_path/'tracking.sqlite3'
    snap=save_snapshot(10,[{'id':1}],[],[],'test',path=path)
    assert snap['status']=='deadline_unknown'
    result={'model':'short_form_3w','risk_profile':'balanced','expected_points':24,
            'risk_adjusted_objective':20,'starting_xi':[{'id':i,'captain':i==1,'xpts':1} for i in range(1,12)],
            'bench':[{'id':i} for i in range(12,16)]}
    first=save_prediction(snap['id'],result,path=path)
    second=save_prediction(snap['id'],result,path=path)
    assert first['id']!=second['id']
    assert get_prediction(first['id'],path)['raw_expected_points']==12
    assert evaluate_prediction(first['id'],{},path)['status']=='incomplete'
    actual={str(i):3 for i in range(1,12)}
    evaluation=evaluate_prediction(first['id'],actual,path)
    assert evaluation['actual_points']==36
    assert evaluation['error_actual_minus_expected']==24
    assert evaluation['risk_adjusted_objective']==20
    with connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('UPDATE predictions SET status=? WHERE id=?',('verified_pre_deadline',first['id']))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM snapshots WHERE id=?',(snap['id'],))


def test_missing_snapshot_and_data(tmp_path):
    path=tmp_path/'tracking.sqlite3'
    with pytest.raises(ValueError): save_snapshot(10,[],[],[],'test',path=path)
    with pytest.raises(ValueError): save_prediction('missing',{},path=path)


def test_complete_nested_lineup_round_trips_and_stays_immutable(tmp_path):
    path=tmp_path/'tracking.sqlite3'
    players=[{'id':i,'name':f'Oyuncu {i}','club_id':17,'position':'MID',
              'price':5.5,'availability':{'status':'AVAILABLE','percent':100}}
             for i in range(1,16)]
    fixtures=[{'id':301,'homeClubId':17,'awayClubId':3,
               'kickoffAt':'2026-11-01T18:00:00Z','metadata':{'source':'TFF'}}]
    histories=[{'player_id':i,'rows':[{'gameweekOrder':9,'points':3,'xG':.4}]}
               for i in range(1,16)]
    source={'players':{'provider':'TFF','retrieved_at':'2026-10-29T10:00:00Z'},
            'external':['xgEdge','TFF fixtures']}
    quality={'crosswalk_version':'abc123','warnings':['missing historical status']}
    snapshot=save_snapshot(10,players,fixtures,histories,source,data_quality=quality,path=path)
    lineup={'model':'short_form_3w','risk_profile':'balanced','expected_points':40,
            'risk_adjusted_objective':38.2,'formation':'4-4-2',
            'starting_xi':[{'id':i,'name':f'Oyuncu {i}','team':'17','price':5.5,
                            'xpts':3.0,'captain':i==1,'metadata':{'fixture':301}}
                           for i in range(1,12)],
            'bench':[{'id':i,'metadata':{'role':'reserve'}} for i in range(12,16)],
            'model_metadata':{'parameters':{'window':3,'risk':{'pair_penalty':.18}}}}
    prediction=save_prediction(snapshot['id'],lineup,path=path)
    stored_snapshot=get_snapshot(snapshot['id'],path)
    stored_prediction=get_prediction(prediction['id'],path)
    assert stored_snapshot['source']==source
    assert stored_snapshot['payload']['fixtures']==fixtures
    assert stored_snapshot['payload']['data_quality']==quality
    assert stored_prediction['payload']['model_metadata']==lineup['model_metadata']
    assert stored_prediction['snapshot_id']==snapshot['id']
    with connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('UPDATE snapshots SET source=? WHERE id=?',('{}',snapshot['id']))
