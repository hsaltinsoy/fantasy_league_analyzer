"""Discover real football club IDs from club-stats/fixtures API, without exporting credentials."""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

PATHS = (
    '/api/backend/projection/stats/club-stats',
    '/api/backend/projection/stats/fixtures',
    '/api/backend/fixture/leagues/1/gameweeks',
)
ID_KEYS = ('clubId', 'club_id', 'teamId', 'team_id')
NAME_KEYS = ('clubName', 'club_name', 'teamName', 'team_name', 'clubTitle', 'teamTitle')

def walk(obj, path='', depth=0):
    if depth > 12: return
    if isinstance(obj, list):
        for x in obj[:5000]: yield from walk(x, path+'[]', depth+1)
    elif isinstance(obj, dict):
        yield path, obj
        for k,v in obj.items():
            if isinstance(v, (list,dict)):
                yield from walk(v, path+'.'+str(k), depth+1)

def inspect(payload, source, candidates, shapes):
    for path, d in walk(payload):
        keys = sorted(str(k) for k in d.keys())
        if any(x in str(path).lower() for x in ('club','team','fixture','match','home','away')) or any('club' in k.lower() for k in keys):
            if len(shapes[source]) < 35:
                shapes[source].setdefault(path, keys[:40])
        # Only record explicit club-prefixed identifiers and names in the same object.
        for ik in ID_KEYS:
            for nk in NAME_KEYS:
                if ik in d and nk in d and isinstance(d[ik], (int,str)) and isinstance(d[nk],str) and d[nk].strip():
                    candidates[str(d[ik])].add((d[nk].strip(), source, path))
        # Explicit nested club fields, not arbitrary fantasy-team id/name.
        for k in ('club','homeClub','awayClub','home_club','away_club'):
            v=d.get(k)
            if isinstance(v,dict):
                ident=v.get('clubId',v.get('id'))
                name=v.get('clubName',v.get('name'))
                if isinstance(ident,(str,int)) and isinstance(name,str) and name.strip():
                    candidates[str(ident)].add((name.strip(),source,path+'.'+k))

def main():
    if not PROFILE.exists(): raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın.')
    candidates=defaultdict(set); shapes=defaultdict(dict); results={}
    with _browser() as pw:
        ctx=pw.chromium.launch_persistent_context(str(PROFILE),headless=False)
        try:
            page=ctx.pages[0] if ctx.pages else ctx.new_page()
            def capture(resp):
                path=urlsplit(resp.url).path
                if path not in PATHS: return
                try: inspect(resp.json(),path,candidates,shapes)
                except Exception: pass
            page.on('response',capture)
            page.goto(BASE,wait_until='domcontentloaded',timeout=60000)
            for path in PATHS:
                try:
                    r=ctx.request.get(BASE+path,timeout=30000)
                    results[path]={'status':r.status,'ok':r.ok}
                    if r.ok: inspect(r.json(),path,candidates,shapes)
                except Exception as exc:
                    results[path]={'error_type':type(exc).__name__}
            print('Sitede kulüp istatistikleri ve fikstür ekranlarını açın. Bitince Enter.')
            input()
        finally: ctx.close()
    out={'classification':'API_CLUB_CANDIDATES_NOT_HISTORICAL_PROOF',
         'captured_utc':datetime.now(timezone.utc).isoformat(),
         'endpoint_status':results,
         'club_id_to_names':{k:sorted({x[0] for x in v}) for k,v in candidates.items()},
         'club_evidence':{k:[{'name':n,'endpoint':s,'json_path':p} for n,s,p in sorted(v)] for k,v in candidates.items()},
         'response_field_shapes':dict(shapes),
         'note':'No response bodies, auth tokens, cookies, or profile data exported. Historical memberships not verified.'}
    target=Path('tff_club_mapping_v2.json');target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(candidates)} explicit club candidates; saved {target.resolve()}')
if __name__=='__main__': main()
