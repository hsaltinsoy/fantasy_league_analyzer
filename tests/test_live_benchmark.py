import copy
from datetime import datetime, timezone

import pytest

from analysis import live_benchmark as benchmark
from analysis.prediction_tracking import get_prediction, get_snapshot


NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def archive():
    def match(mid, week, status='SCHEDULED'):
        return {'id':mid,'homeClubId':1,'awayClubId':2,'kickoffAt':f'2026-10-{week}T17:00:00Z',
                'status':status,'homeScore':None,'awayScore':None}
    return {'source_endpoint':benchmark.FIXTURE_ENDPOINT,'captured_utc':NOW.isoformat(),
            'weeks':{'9':{'gameweek_id':90,'deadline':'2026-10-28T16:00:00Z','matches':[match(9,28,'FT')]},
                     '10':{'gameweek_id':100,'deadline':'2026-10-30T16:00:00Z','matches':[match(10,30)]},
                     '11':{'gameweek_id':110,'deadline':'2026-10-31T16:00:00Z','matches':[match(11,31)]}}}


def test_next_week_uses_official_future_fixture():
    assert benchmark.next_gameweek(archive(), NOW)[0] == 10
    with pytest.raises(ValueError):
        benchmark.next_gameweek(archive(), datetime(2026, 11, 1, tzinfo=timezone.utc))


def test_shared_snapshot_model_isolation_and_deadline(tmp_path, monkeypatch):
    players = [{'id':i,'name':f'P{i}','position':'DEF','price':5,'club_id':1 if i%2 else 2}
               for i in range(1,16)]
    records = [(dict(p), [{'gameweekOrder':9,'points':3,'minutesPlayed':90}]) for p in players]
    original = copy.deepcopy(players)
    seen = []

    def fake_predict(week, input_players, input_records, fixtures, tow, model='short_form_3w', **kwargs):
        assert week == 10
        assert input_players == original
        assert input_records == records
        assert fixtures == {10:{'1':'2','2':'1'}}
        seen.append(model)
        input_players[0]['name'] = 'mutated locally'
        xi = [dict(p,team=str(p['club_id']),opponent=str(2 if p['club_id']==1 else 1),
                   xpts=4.,captain=p['id']==1) for p in input_players[:11]]
        return {'model':model,'risk_profile':'balanced','starting_xi':xi,
                'bench':input_players[11:],'formation':'4-4-2','cost':75}

    monkeypatch.setattr(benchmark,'predict',fake_predict)
    monkeypatch.setattr(benchmark,'load_crosswalk',lambda: {})
    monkeypatch.setattr(benchmark,'crosswalk_version',lambda _: 'test-version')
    monkeypatch.setattr('analysis.team_of_week_v36.load',lambda _: {})
    result = benchmark.generate(fixture_archive=archive(),players=players,records=records,
                                path=tmp_path/'tracking.sqlite3',now=NOW)
    assert len(result['predictions']) == len(benchmark.MODELS)
    assert all(p['snapshot_id']==result['snapshot']['id'] for p in result['predictions'])
    assert all(p['status']=='locally_recorded_pre_deadline_not_verified' for p in result['predictions'])
    assert get_snapshot(result['snapshot']['id'],tmp_path/'tracking.sqlite3')['payload']['players']==original
    stored=get_snapshot(result['snapshot']['id'],tmp_path/'tracking.sqlite3')
    assert stored['deadline_source']=='https://tfffantezilig.com/api/backend/projection/stats/fixtures?league-id=1'
    assert stored['source']['deadline_retrieved_at']==NOW.isoformat()
    assert stored['source']['official_gameweek_id']==100
    assert len(seen)==len(benchmark.MODELS)+1  # covariance attempt is isolated too
    first = get_prediction(result['predictions'][0]['id'],tmp_path/'tracking.sqlite3')
    assert first['payload']['benchmark']['snapshot_id']==result['snapshot']['id']
    assert first['raw_expected_points']==48
    assert result['variants']['appearance'].startswith('not_evaluable')


def test_cached_mode_is_reconstruction_and_missing_deadline_is_unknown(tmp_path, monkeypatch):
    data = archive()
    data['weeks']['10']['deadline'] = None
    players = [{'id':i,'name':f'P{i}','position':'DEF','price':5,'club_id':1} for i in range(15)]
    records = [(p,[{'gameweekOrder':9,'points':1}]) for p in players]
    monkeypatch.setattr(benchmark,'load_crosswalk',lambda: {})
    monkeypatch.setattr(benchmark,'crosswalk_version',lambda _: 'v')
    monkeypatch.setattr('analysis.team_of_week_v36.load',lambda _: {})
    def fake(*args,**kwargs):
        xi=[dict(p,xpts=1,team='1',opponent='2',captain=p['id']==0) for p in args[1][:11]]
        return {'model':kwargs.get('model','short_form_3w'),'risk_profile':'balanced',
                'starting_xi':xi,'bench':args[1][11:],'formation':'4-4-2','cost':75}
    monkeypatch.setattr(benchmark,'predict',fake)
    out=benchmark.generate(fixture_archive=data,players=players,records=records,
                           path=tmp_path/'tracking.sqlite3',now=NOW,cached=True)
    assert out['snapshot']['status']=='historical_reconstruction_not_verified'
    assert 'official_deadline_missing_or_invalid' in out['data_quality']['warnings']
    assert all(p['status']=='historical_reconstruction_not_verified' for p in out['predictions'])


def test_report_requires_complete_actuals(tmp_path, monkeypatch):
    counts=benchmark.report(tmp_path/'absent.sqlite3')['counts']
    assert counts['verified']==counts['unverified']==counts['complete_evaluations']==0


def test_official_completion_gate_and_dashboard():
    data = archive()
    assert not benchmark._results_complete(data, 10)
    data['weeks']['10']['matches'][0]['status'] = 'FT'
    assert benchmark._results_complete(data, 10)
    from app import create_app
    response = create_app().test_client().get('/benchmark')
    assert response.status_code == 200
    assert b'Prediction benchmark' in response.data
