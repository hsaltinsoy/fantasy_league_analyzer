"""Download official historical dream teams using existing authenticated browser profile."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

ENDPOINT = '/api/backend/projection/stats/dream-team?leagueId=1&type=week&gameweekId={week}'

def parse(payload, week):
    if not isinstance(payload, dict) or payload.get('status') not in (True, 'success', 'ok', 200, None):
        raise ValueError(f'GW{week}: API error')
    data = payload.get('data')
    if not isinstance(data, dict) or data.get('available') is False:
        raise ValueError(f'GW{week}: no available dream team')
    players = data.get('players') if isinstance(data, dict) else None
    if not isinstance(players, list) or len(players) != 11:
        raise ValueError(f'GW{week}: expected 11 players, got {len(players) if isinstance(players,list) else "none"}')
    seen=set(); output=[]
    for player in players:
        pid=player.get('playerId')
        if isinstance(pid,bool) or not isinstance(pid,int) or pid<=0 or pid in seen:
            raise ValueError(f'GW{week}: invalid/duplicate playerId {pid}')
        seen.add(pid)
        output.append({'player_id':pid,'name':player.get('name'),'position':player.get('position'),
                       'club_id':player.get('clubId'),'points':player.get('points')})
    return {'players':output,'formation':data.get('formation'),'total_points':data.get('totalPoints'),
            'source_gameweek_id':data.get('gameweekId')}

def fetch(weeks, destination):
    if not PROFILE.exists():
        raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın')
    collected={};errors={}
    with _browser() as pw:
        browser=pw.chromium.launch_persistent_context(str(PROFILE),headless=True)
        try:
            for week in weeks:
                url=BASE+ENDPOINT.format(week=week)
                try:
                    response=browser.request.get(url,timeout=45000)
                    if response.status in (401,403):
                        raise TFFFeedError('Session expired; login again')
                    if not response.ok: raise ValueError(f'HTTP {response.status}')
                    collected[str(week)]=parse(response.json(),week)
                    print(f'GW{week}: 11 players',flush=True)
                except (ValueError, KeyError) as exc:
                    errors[str(week)]=str(exc);print(f'GW{week}: {exc}',flush=True)
        finally:browser.close()
    result={'source_endpoint':ENDPOINT,'classification':'RETROSPECTIVE_API_FETCH_NOT_PREDEADLINE_SNAPSHOT',
            'fetched_utc':datetime.now(timezone.utc).isoformat(), 'weeks':collected,'errors':errors}
    dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--weeks',nargs='+',type=int,default=list(range(1,10)))
    p.add_argument('--output',default='historical_data/team_of_week_verified.json')
    args=p.parse_args()
    if len(set(args.weeks))!=len(args.weeks) or min(args.weeks)<1:p.error('Invalid weeks')
    result=fetch(args.weeks,args.output)
    print(f"Saved {len(result['weeks'])} weeks, {len(result['errors'])} errors: {args.output}")
if __name__=='__main__':main()
