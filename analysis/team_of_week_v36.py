"""Historical team-of-week features. Only rounds strictly before prediction week."""
import json
from pathlib import Path

def load(path):
    payload=json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('classification')!='RETROSPECTIVE_API_FETCH_NOT_PREDEADLINE_SNAPSHOT':
        raise ValueError('Unknown team-of-week provenance')
    result={}
    for w,record in payload.get('weeks',{}).items():
        players=record.get('players')
        if not isinstance(players,list) or len(players)!=11:raise ValueError(f'GW{w}: incomplete')
        ids=[p['player_id'] for p in players]
        if len(set(ids))!=11:raise ValueError(f'GW{w}: duplicates')
        result[int(w)]=set(ids)
    if not result:raise ValueError('No complete team-of-week data')
    return result

def feature(weeks, week, player_id):
    prior=sorted(w for w in weeks if w<week)
    recent=prior[-5:]
    # Missing weeks are NOT silently assumed to be negative observations.
    last3=recent[-3:]
    return {'last3':sum(player_id in weeks[w] for w in last3),
            'last5':sum(player_id in weeks[w] for w in recent),
            'coverage3':len(last3),'coverage5':len(recent)}

def boost(weeks, week, player_id, weight):
    f=feature(weeks,week,player_id)
    if not f['coverage5']:return 1.0
    # Small, capped uplift, with stronger emphasis on recent membership.
    signal=.65*f['last3']/max(1,f['coverage3'])+.35*f['last5']/f['coverage5']
    return 1+weight*signal
