import json
import zipfile

import pytest

from analysis.recovered_history import build
from analysis.recovered_model_evaluation import (_positions_for_week, evaluate,
    forecast_with_prior_position)
from analysis.multiweek_backtest import MODELS, project
from data_sources.historical_recovery import _save_raw, collect_official
from data_sources.team_of_week import ENDPOINT as DREAM_ENDPOINT
from data_sources.tff_official import BASE


def test_raw_official_payload_is_content_addressed_and_provenanced(tmp_path):
    payload={'data':[{'playerId':1,'position':'GK'}]}
    first=_save_raw(payload,'players',BASE+'/official','2026-10-29T12:00:00Z',tmp_path)
    second=_save_raw(payload,'players',BASE+'/official','2026-10-30T12:00:00Z',tmp_path)
    assert first['sha256']==second['sha256']
    assert first['relative_path']==second['relative_path']
    assert first['retrieved_at']!=second['retrieved_at']
    assert first['evidence_quality'].endswith('not_deadline_verified')
    assert len(list((tmp_path/'raw'/'official').glob('*.json')))==1


def test_collector_uses_existing_profile_and_stops_on_access_denial(tmp_path,monkeypatch):
    import data_sources.historical_recovery as module
    profile=tmp_path/'profile'
    profile.mkdir()
    monkeypatch.setattr(module,'PROFILE',profile)
    monkeypatch.setattr(module.time,'sleep',lambda _:None)
    dream={'data':{'available':True,'gameweekId':1,'players':[
        {'playerId':i,'position':'MID','clubId':1} for i in range(1,12)]}}
    class Response:
        status=200
        ok=True
        def __init__(self,payload):self.payload=payload
        def json(self):return self.payload
    class Request:
        def __init__(self,deny=False):self.calls=[];self.deny=deny
        def get(self,url,timeout):
            self.calls.append(url)
            if self.deny:
                r=Response({});r.status=401;r.ok=False;return r
            if 'dream-team' in url:return Response(dream)
            if 'fixtures' in url:return Response({'data':{'gameweeks':[]}})
            if 'club-stats' in url:return Response({'data':[{'id':1,'name':'Club One'}]})
            return Response({'data':[{'playerId':1,'position':'MID'}]})
    class Context:
        def __init__(self,request):self.request=request
        def close(self):pass
    class Browser:
        def __init__(self,request):self.request=request
        def launch_persistent_context(self,path,headless):
            assert path==str(profile) and headless
            return Context(self.request)
    class Session:
        def __init__(self,request):self.chromium=Browser(request)
        def __enter__(self):return self
        def __exit__(self,*_):pass
    request=Request()
    monkeypatch.setattr(module,'_browser',lambda:Session(request))
    result=collect_official(tmp_path/'recovered',weeks=[1])
    assert set(result['entries'])=={'player_stats_current','fixtures_current','clubs_current','dream_team_gw1'}
    assert request.calls[-1]==BASE+DREAM_ENDPOINT.format(week=1)
    denied=Request(deny=True)
    monkeypatch.setattr(module,'_browser',lambda:Session(denied))
    with pytest.raises(module.TFFFeedError,match='401'):
        collect_official(tmp_path/'denied',weeks=[1])


def test_position_evidence_uses_only_earlier_weeks_and_rejects_conflicts():
    data={'players':{'1':[{'effective_gameweek':3,'position':'DEF','source_url':'official',
                           'retrieved_at':'late'},
                          {'effective_gameweek':9,'position':'MID','source_url':'official',
                           'retrieved_at':'late'}]}}
    positions,conflicts=_positions_for_week(data,9)
    assert positions['1']['position']=='DEF'
    assert positions['1']['source_effective_week']==3
    assert not conflicts
    positions,conflicts=_positions_for_week(data,10)
    assert '1' not in positions and conflicts=={'1'}
    mixed={'players':{'2':[{'effective_gameweek':0,'position':'MID',
                             'source_url':'workbook','retrieved_at':'late',
                             'quality':'third_party_preseason_workbook'}]}}
    assert '2' in _positions_for_week(mixed,9,'combined')[0]
    assert '2' not in _positions_for_week(mixed,9,'official_only')[0]


def test_recovered_form_forecast_matches_existing_model_and_rejects_future_rows():
    past=[{'gameweekOrder':week,'points':week%4,'minutesPlayed':90}
          for week in range(1,9)]
    expected=project({'position':'MID'},past,MODELS['stable_8w'])
    assert forecast_with_prior_position('MID',past,9,'stable_8w')==expected
    with pytest.raises(ValueError,match='future'):
        forecast_with_prior_position('MID',past+[{'gameweekOrder':9,'points':50,
                                                 'minutesPlayed':90}],9,'stable_8w')
    with pytest.raises(ValueError,match='Insufficient'):
        forecast_with_prior_position('MID',past[:7],9,'stable_8w')


def synthetic_recovery(tmp_path):
    store=tmp_path/'archive';store.mkdir()
    out=tmp_path/'recovered';out.mkdir()
    players=[{'playerId':i,'name':'Player','surname':str(i),
              'position':'MID','clubId':1} for i in range(1,12)]
    fixtures={'data':{'gameweeks':[{'id':week,'order':week,
        'deadline':f'2026-08-{week+10:02d}T12:00:00Z',
        'matches':[{'id':week,'homeClubId':1,'awayClubId':2,'status':'FT',
                    'homeScore':1,'awayScore':0}]} for week in range(1,10)]}}
    entries={'player_stats_current':_save_raw({'data':players},'players',BASE+'/players',
                            '2026-10-29T12:00:00Z',out),
             'fixtures_current':_save_raw(fixtures,'fixtures',BASE+'/fixtures',
                            '2026-10-29T12:00:00Z',out),
             'clubs_current':_save_raw({'data':[{'id':1,'name':'Club One'},
                                               {'id':2,'name':'Club Two'}]},'clubs',BASE+'/clubs',
                            '2026-10-29T12:00:00Z',out)}
    for week in range(1,10):
        dream={'data':{'available':True,'gameweekId':week,
                       'players':[{'playerId':i,'position':'MID','clubId':1}
                                  for i in range(1,12)]}}
        entries[f'dream_team_gw{week}']=_save_raw(dream,f'dream_team_gw{week}',
            BASE+DREAM_ENDPOINT.format(week=week),'2026-10-29T12:00:00Z',out)
    (out/'official_collection_manifest.json').write_text(json.dumps({'entries':entries}),encoding='utf-8')
    workbook=out/'raw'/'third_party'/'oyuncu_veritabani_f1368196.xlsx'
    workbook.parent.mkdir(parents=True)
    xml=('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
         '<sheetData><row r="5"><c r="A5" t="inlineStr"><is><t>PLY001</t></is></c>'
         '<c r="B5" t="inlineStr"><is><t>Player 1</t></is></c>'
         '<c r="C5" t="inlineStr"><is><t>MID - Midfielder</t></is></c>'
         '<c r="D5" t="inlineStr"><is><t>Club One</t></is></c></row>'
         '<row r="6"><c r="A6" t="inlineStr"><is><t>PLY002</t></is></c>'
         '<c r="B6" t="inlineStr"><is><t>Player 2</t></is></c>'
         '<c r="C6" t="inlineStr"><is><t>DEF - Defender</t></is></c>'
         '<c r="D6" t="inlineStr"><is><t>Wrong Club</t></is></c></row>'
         '</sheetData></worksheet>')
    with zipfile.ZipFile(workbook,'w') as archive:
        archive.writestr('xl/worksheets/sheet1.xml',xml)
    for pid in range(1,12):
        rows=[]
        for week in range(1,10):
            transferred=pid==1 and week>=5
            rows.append({'gameweekOrder':week,'gameweekId':week,'points':2,
                'minutesPlayed':90,'played':True,'cost':5.,
                'opponentClubId':1 if transferred else 2,
                'homeAway':'A' if transferred else 'H'})
        (store/f'player_{pid}.json').write_text(json.dumps(rows),encoding='utf-8')
    return store,out


def test_recovered_clubs_transfers_and_model_samples_are_retrospective(tmp_path):
    store,out=synthetic_recovery(tmp_path)
    coverage=build(store,out)
    assert coverage['position_unique_player_ids']==11
    assert coverage['preseason_workbook_matched_ids']==1
    assert coverage['preseason_workbook_exclusions']['club_name_mismatch']==1
    assert coverage['transfer_player_count']==1
    assert coverage['weeks'][0]['prior_official_position']==0
    assert coverage['weeks'][1]['prior_official_position']==11
    assert all(week['deadline_availability']==0 and not week['full_xi_feasible']
               for week in coverage['weeks'])
    repeated=build(store,out)
    assert repeated['snapshots']==coverage['snapshots']
    assert repeated['position_evidence']==coverage['position_evidence']
    result=evaluate(store,out)
    assert result['matched_all_models']['weeks']==[9]
    assert result['matched_all_models']['n']==11
    assert all(item['unconditional']['n']==11 for item in
               result['matched_all_models']['models'].values())
    assert result['by_gameweek'][0]['available_models']==[]
    assert result['by_gameweek'][2]['available_models']==['short_form_3w']
    assert result['classification'].startswith('retrospective')


def test_recovered_source_digest_corruption_is_rejected(tmp_path):
    store,out=synthetic_recovery(tmp_path)
    manifest=json.loads((out/'official_collection_manifest.json').read_text(encoding='utf-8'))
    path=out/manifest['entries']['fixtures_current']['relative_path']
    path.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='digest mismatch'):
        build(store,out)


def test_benchmark_shows_recovery_coverage_and_selected_model_sample(monkeypatch):
    from app import create_app
    from analysis import live_benchmark
    monkeypatch.setattr(live_benchmark,'report',lambda **kwargs:{
        'predictions':[],'evaluation_runs':[],'by_model':{},
        'counts':{'verified':0,'unverified':0,'complete_evaluations':0,
                  'locally_recorded_pre_deadline':0,'post_deadline':0}})
    client=create_app().test_client()
    page=client.get('/benchmark')
    assert page.status_code==200
    html=page.get_data(as_text=True)
    assert 'Recovered historical data' in html
    assert 'prior-week position' in html
    assert '60 matched players' in html
    assert 'Not evaluable' in html
    assert client.get('/api/benchmark/recovered-history').status_code==200
    assert client.get('/api/benchmark/recovered-models').status_code==200
