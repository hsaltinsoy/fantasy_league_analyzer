from copy import deepcopy

from app import create_app
from app.benchmark_view import comparison_view


def fixture_data():
    players = []
    for i, position in enumerate(['GK','DEF','DEF','DEF','DEF','MID','MID','MID','MID','FWD','FWD'],1):
        players.append({'id':i,'name':f'Player {i}','team':'7','position':position,
                        'xpts':float(i),'captain':i==10})
    other = deepcopy(players)
    other[-1] = {'id':12,'name':'New striker','team':'8','position':'FWD','xpts':8.,'captain':True}
    other[-2]['captain'] = False
    snapshot = {'id':'shared-snapshot','source':{'fixtures_retrieved_at':'2026-10-29T12:00:00Z'},
                'payload':{'data_quality':{'fixture_source_age_hours':0.2}}}
    saved = {
        'a':{'id':'a','snapshot_id':'shared-snapshot','gameweek':10,'model':'short_form_3w',
             'model_version':'phase6.1','risk_strategy':'balanced','status':'deadline_unknown',
             'raw_expected_points':66.,'risk_adjusted_objective':65.,
             'payload':{'starting_xi':players,'formation':'4-4-2','budget_remaining':15.,'cost':85.}},
        'b':{'id':'b','snapshot_id':'shared-snapshot','gameweek':10,'model':'experimental_covariance',
             'model_version':'phase6.1','risk_strategy':'experimental_lambda_1','status':'deadline_unknown',
             'raw_expected_points':67.,'risk_adjusted_objective':50.,
             'payload':{'starting_xi':other,'formation':'4-4-2','cost':86.}},
    }
    rows = [{'id':key,'gameweek':10,'model':value['model'],'model_version':'phase6.1',
             'created_at':'2026-10-29T12:00:00Z','verification_status':'deadline_unknown',
             'provenance':{'deadline_at':'2026-10-30T16:00:00Z','deadline_timezone':'UTC',
                           'deadline_source_url':'https://tfffantezilig.com/api/backend/projection/stats/fixtures?league-id=1'},
             'snapshot_id':'shared-snapshot','captain':'Player 10' if key=='a' else 'New striker',
             'expected_points':value['raw_expected_points'],
             'evaluation':{'status':'not_evaluable'},'source':{'fixtures':'official'},
             'data_quality':{'fixture_source_age_hours':0.2,'warnings':[]}}
            for key,value in saved.items()]
    metrics = {'n':0,'mae':None,'rmse':None}
    report = {'predictions':rows,'evaluation_runs':[],
              'counts':{'verified':0,'unverified':2,'complete_evaluations':0,
                        'locally_recorded_pre_deadline':0,'post_deadline':0},
              'by_model':{value['model']:{'n':1,'evaluable':0,'team_metrics':metrics,
                                         'player_metrics':metrics,'recent_3_baseline':metrics,
                                         'season_to_date_baseline':metrics} for value in saved.values()}}
    return report,saved,snapshot


def test_comparison_uses_ids_and_saved_values(monkeypatch):
    report,saved,snapshot = fixture_data()
    monkeypatch.setattr('app.benchmark_view.get_prediction',lambda pid: saved[pid])
    monkeypatch.setattr('app.benchmark_view.get_snapshot',lambda sid: snapshot)
    view = comparison_view(report,'a','b',{'7':{'short_name':'Club Seven'}})
    assert view['common_players']==10
    assert len(view['common_players_list'])==10
    assert [p['id'] for p in view['left_unique']]==[11]
    assert [p['id'] for p in view['right_unique']]==[12]
    assert view['captain_different']
    assert not view['formation_different']
    assert view['left']['expected_points']==66.
    assert view['right']['risk_adjusted_objective']==50.
    assert view['right']['remaining_budget']==14.
    assert view['left']['players'][0]['club_label']=='Club Seven'
    assert view['right']['players'][-1]['club_label']=='Club ID 8'
    assert view['same_snapshot']


def test_benchmark_page_renders_two_saved_pitches_and_tables(monkeypatch):
    report,saved,snapshot = fixture_data()
    monkeypatch.setattr('analysis.live_benchmark.report',lambda **kwargs: report)
    monkeypatch.setattr('app.benchmark_view.get_prediction',lambda pid: saved[pid])
    monkeypatch.setattr('app.benchmark_view.get_snapshot',lambda sid: snapshot)
    monkeypatch.setattr('data_sources.club_metadata.load_clubs',lambda: {'7':{'name':'Club Seven'}})
    response = create_app().test_client().get('/benchmark?left=a&right=b')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert html.count('class="pitch"')==2
    assert html.count('class="player-card ') == 22
    assert 'New striker' in html and 'Club Seven' in html and 'Club ID 8' in html
    assert '66.00' in html and '50.00' in html and '14.00' in html
    assert 'Only in first XI' in html and 'Captain / formation' in html
    assert 'shared-snapshot' in html and 'deadline unknown' in html
    assert 'Model evaluation' in html and 'Prediction history' in html
    assert 'Not evaluable' in html and 'predicted pts' in html


def test_benchmark_mobile_styles_and_empty_state(monkeypatch):
    monkeypatch.setattr('analysis.live_benchmark.report',lambda **kwargs: {
        'predictions':[],'evaluation_runs':[],
        'counts':{'verified':0,'unverified':0,'complete_evaluations':0,
                  'locally_recorded_pre_deadline':0,'post_deadline':0},'by_model':{}})
    html = create_app().test_client().get('/benchmark').get_data(as_text=True)
    assert 'No saved benchmark predictions' in html
    css = create_app().test_client().get('/static/benchmark.css')
    assert css.status_code == 200
    assert b'@media(max-width:760px)' in css.data
    assert b'grid-template-columns:1fr' in css.data
