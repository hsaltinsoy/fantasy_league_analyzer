"""Strict, idempotent evaluation of immutable benchmark predictions."""
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone

from analysis.prediction_tracking import (DEFAULT_DB, connect, get_prediction, get_snapshot,
                                          parse_time, save_evaluation_run)
from analysis.production_evaluation import _metrics, evaluate_saved
from analysis.player_ranking_evaluation import ranking_metrics
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

FIXTURE_ENDPOINT='/api/backend/projection/stats/fixtures?league-id=1'
FIXTURE_URL=BASE+FIXTURE_ENDPOINT
PLAYER_HISTORY_URL=BASE+'/api/backend/projection/stats/players/{player_id}/history?league-id=1'
FINISHED={'FT','FINISHED','COMPLETED'}


def fetch_official_player_rows(week, player_ids):
    """Fetch every selected player's official history in one browser session."""
    if not PROFILE.exists():
        raise TFFFeedError('TFF browser profile is missing')
    rows_by_player={}
    with _browser() as pw:
        context=pw.chromium.launch_persistent_context(str(PROFILE),headless=True)
        try:
            for pid in sorted({str(pid) for pid in player_ids},key=int):
                response=context.request.get(PLAYER_HISTORY_URL.format(player_id=pid),timeout=45000)
                if not response.ok:
                    raise TFFFeedError(f'Official player history HTTP {response.status} for {pid}')
                payload=response.json()
                rows=payload.get('data',payload) if isinstance(payload,dict) else payload
                if not isinstance(rows,list):
                    raise TFFFeedError(f'Invalid official player history for {pid}')
                rows_by_player[pid]=[row for row in rows if isinstance(row,dict) and
                                     str(row.get('gameweekOrder'))==str(week)]
        finally:
            context.close()
    return {'rows_by_player':rows_by_player,'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'source_url':PLAYER_HISTORY_URL}


def _fixture_check(snapshot, archive):
    week=snapshot['gameweek']
    url=archive.get('source_url') or (BASE+archive.get('source_endpoint',''))
    retrieved=parse_time(archive.get('captured_utc'))
    if url!=FIXTURE_URL or retrieved is None:
        return None,['untrusted_or_undated_fixture_source']
    entry=(archive.get('weeks') or {}).get(str(week))
    if not isinstance(entry,dict):
        return None,['missing_official_gameweek']
    gameweek_id=entry.get('gameweek_id')
    if isinstance(gameweek_id,bool) or not isinstance(gameweek_id,int) or gameweek_id<1:
        return entry,['missing_official_gameweek_id']
    captured_id=(snapshot.get('source') or {}).get('official_gameweek_id')
    if captured_id is not None and captured_id!=gameweek_id:
        return entry,['gameweek_id_changed_since_snapshot']
    saved=snapshot['payload'].get('fixtures') or []
    live=entry.get('matches') or []
    if not saved or len(saved)!=len(live):
        return entry,['fixture_coverage_mismatch']
    def mapping(matches):
        result={}
        teams=[]
        for match in matches:
            mid=match.get('id')
            home,away=match.get('homeClubId'),match.get('awayClubId')
            if mid is None or home is None or away is None or home==away or mid in result:
                return None
            result[mid]=(str(home),str(away))
            teams.extend((str(home),str(away)))
        if len(set(teams))!=len(teams):
            return None
        return result
    saved_map,live_map=mapping(saved),mapping(live)
    if saved_map is None or live_map is None or saved_map!=live_map:
        return entry,['fixture_id_or_club_mismatch']
    if any(str(match.get('status') or '').upper() not in FINISHED or
           match.get('homeScore') is None or match.get('awayScore') is None for match in live):
        return entry,['official_fixtures_incomplete']
    return entry,[]


def _actual_check(snapshot, entry, fetched, selected_ids, *, allow_local_archive=False):
    url=fetched.get('source_url')
    valid_source=url==PLAYER_HISTORY_URL or (allow_local_archive and
                                             isinstance(url,str) and url.startswith('local_archive:'))
    if not valid_source or parse_time(fetched.get('retrieved_at')) is None:
        raise ValueError('Official player results have no valid source URL or retrieval time')
    rows_by_player=fetched.get('rows_by_player')
    if not isinstance(rows_by_player,dict):
        raise ValueError('Official player results must be keyed by player ID')
    expected_ids={str(pid) for pid in selected_ids}
    if set(rows_by_player)-expected_ids:
        raise ValueError('Unexpected player IDs in official result response')
    players={str(p['id']):p for p in snapshot['payload'].get('players',[])}
    fixtures={}
    for match in entry['matches']:
        home,away=str(match['homeClubId']),str(match['awayClubId'])
        fixtures[home]=(away,'H')
        fixtures[away]=(home,'A')
    actual={}
    issues={}
    for pid in sorted(expected_ids,key=int):
        rows=rows_by_player.get(pid)
        if not isinstance(rows,list) or len(rows)!=1:
            issues[pid]='missing_or_duplicate_gameweek_result'
            continue
        row=rows[0]
        if not isinstance(row,dict):
            issues[pid]='invalid_gameweek_result'
            continue
        player=players.get(pid)
        club=str(player.get('club_id') or player.get('team')) if player else None
        fixture=fixtures.get(club)
        if player is None or fixture is None:
            issues[pid]='player_or_club_missing_from_snapshot_fixture'
        elif str(row.get('gameweekOrder'))!=str(snapshot['gameweek']) or row.get('gameweekId')!=entry['gameweek_id']:
            issues[pid]='gameweek_id_or_order_mismatch'
        elif row.get('playerId') is not None and str(row['playerId'])!=pid:
            issues[pid]='player_id_mismatch'
        elif str(row.get('opponentClubId'))!=fixture[0] or row.get('homeAway')!=fixture[1]:
            issues[pid]='opponent_or_venue_mismatch'
        elif isinstance(row.get('points'),bool) or not isinstance(row.get('points'),(int,float)) or not math.isfinite(row['points']):
            issues[pid]='missing_or_invalid_points'
        else:
            actual[pid]=float(row['points'])
    return actual,issues


def _digest(fixture_entry, rows_by_player, prediction_ids):
    normalized_entry=dict(fixture_entry) if fixture_entry is not None else None
    if normalized_entry is not None and isinstance(normalized_entry.get('matches'),list):
        normalized_entry['matches']=sorted(normalized_entry['matches'],
                                           key=lambda match: str(match.get('id')))
    content={'fixture_entry':normalized_entry,'actual_rows':rows_by_player,
             'prediction_ids':sorted(prediction_ids)}
    return hashlib.sha256(json.dumps(content,sort_keys=True,ensure_ascii=False,
                                     separators=(',',':')).encode('utf-8')).hexdigest()


def evaluate_gameweek(snapshot_id, *, fixture_archive=None, rows_provider=None, path=DEFAULT_DB):
    """Persist one run per distinct official evidence set; never update predictions."""
    snapshot=get_snapshot(snapshot_id,path)
    if snapshot is None:
        raise ValueError('Unknown immutable snapshot')
    week=snapshot['gameweek']
    from analysis.prediction_tracking import _postgres
    pg = _postgres(path)
    if pg:
        ids = pg.prediction_ids(snapshot_id)
    else:
        with connect(path) as db:
            ids=[row[0] for row in db.execute('SELECT id FROM predictions WHERE snapshot_id=? ORDER BY created_at,id',
                                              (snapshot_id,))]
    predictions=[get_prediction(pid,path) for pid in ids]
    predictions=[p for p in predictions if 'benchmark' in p['payload']]
    if not predictions:
        raise ValueError('Snapshot has no benchmark predictions')
    for prediction in predictions:
        if prediction['gameweek']!=week or prediction['payload'].get('week',week)!=week or \
           prediction['payload']['benchmark'].get('snapshot_id',snapshot_id)!=snapshot_id:
            raise ValueError('Saved prediction references an inconsistent snapshot or gameweek')
    if fixture_archive is None:
        from analysis.live_benchmark import fetch_official_fixtures
        fixture_archive=fetch_official_fixtures()
    entry,fixture_issues=_fixture_check(snapshot,fixture_archive)
    selected_ids={str(player['id']) for prediction in predictions
                  for player in prediction['payload'].get('starting_xi',[])}
    fetched=None
    actual={}
    player_issues={}
    if not fixture_issues:
        fetched=(rows_provider or fetch_official_player_rows)(week,selected_ids)
        actual,player_issues=_actual_check(snapshot,entry,fetched,selected_ids)
    results={}
    for prediction in predictions:
        if fixture_issues:
            evaluation={'status':'incomplete','reason':fixture_issues[0],
                        'verification_status':prediction['status']}
        else:
            evaluation=evaluate_saved(prediction,snapshot['payload'],actual)
            if 'actual_points' in evaluation:
                evaluation['status']='complete'
                evaluation['verification_status']=prediction['status']
                ranking_rows=[{'player_id':str(player['id']),
                               'actual':float(actual[str(player['id'])]),
                               'predictions':{'saved_forecast':float(player['xpts'])}}
                              for player in prediction['payload']['starting_xi']]
                evaluation['xi_ranking']=ranking_metrics(ranking_rows,'saved_forecast')
                evaluation['xi_ranking']['population']='selected_starting_xi_only'
            else:
                evaluation['status']='incomplete'
                invalid={str(p['id']):player_issues[str(p['id'])] for p in prediction['payload']['starting_xi']
                         if str(p['id']) in player_issues}
                if invalid:
                    evaluation['player_issues']=invalid
        results[prediction['id']]=evaluation
    complete=[r for r in results.values() if r['status']=='complete']
    status='complete' if len(complete)==len(predictions) else 'incomplete'
    groups=defaultdict(list)
    for prediction in predictions:
        row=results[prediction['id']]
        if row['status']=='complete':
            groups[prediction['model']].append(row)
    by_model={model:{'predictions':sum(p['model']==model for p in predictions),
                     'complete':len(rows),'team_metrics':_metrics([r['error'] for r in rows]),
                     'player_metrics':_metrics([p['error'] for r in rows for p in r['players']])}
              for model,rows in groups.items()}
    fixture_url=fixture_archive.get('source_url') or (BASE+fixture_archive.get('source_endpoint',''))
    source={'fixture_url':fixture_url,'fixtures_retrieved_at':fixture_archive.get('captured_utc'),
            'actuals_url_template':PLAYER_HISTORY_URL if fetched else None,
            'actuals_retrieved_at':fetched.get('retrieved_at') if fetched else None,
            'official_gameweek_id':entry.get('gameweek_id') if entry else None,
            'timezone':'UTC'}
    payload={'official_fixture_entry':entry,
             'official_actual_rows':fetched.get('rows_by_player') if fetched else None,
             'fixture_issues':fixture_issues,'player_issues':player_issues,
             'selected_player_count':len(selected_ids),'valid_actual_player_count':len(actual),
             'prediction_results':results,'by_model':by_model,
             'complete_predictions':len(complete),'total_predictions':len(predictions),
             'limitations':['A single gameweek cannot establish model superiority.',
                            'Ranking is within each selected XI; complete candidate-pool rankings were not saved.',
                            'No missing appearance or result is replaced with zero.',
                            'Existing GW10 snapshot lacks the official gameweek ID at capture; current official ID is checked against player rows and saved fixture IDs.']}
    digest=_digest(entry,fetched.get('rows_by_player') if fetched else None,[p['id'] for p in predictions])
    return save_evaluation_run(snapshot_id,week,digest,status,source,payload,path)
