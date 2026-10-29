"""Diagnose fantasy fixture API responses without exporting tokens or private user data."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

OUT = Path('tff_fixture_diagnostic_v4.json')
PATHS = ('/api/backend/projection/stats/fixtures', '/api/backend/fixture/leagues/1/gameweeks')

def scan(obj, path='$', depth=0):
    if depth > 15: return
    if isinstance(obj, dict):
        yield path, obj
        for k,v in obj.items():
            if isinstance(v,(dict,list)): yield from scan(v, path+'.'+str(k),depth+1)
    elif isinstance(obj,list):
        for i,v in enumerate(obj[:1000]):
            if isinstance(v,(dict,list)): yield from scan(v, path+f'[{i}]',depth+1)

def summarize(payload):
    matches=[]; shapes=[]; collections=[]
    for path,obj in scan(payload):
        keys=list(obj)
        if 'homeClubId' in obj and 'awayClubId' in obj:
            matches.append({k:obj.get(k) for k in ('id','homeClubId','awayClubId','kickoffAt','gameweekId','gameweek','gameweekNumber','week','round') if k in obj})
        if any(k in obj for k in ('matches','fixtures','gameweeks','homeClubId','awayClubId')) and len(shapes)<30:
            shapes.append({'path':path,'keys':keys[:35]})
        for k,v in obj.items():
            if isinstance(v,list) and len(collections)<25:
                collections.append({'path':path+'.'+k,'length':len(v),'first_item_keys':list(v[0])[:35] if v and isinstance(v[0],dict) else []})
    return {'top_level_type':type(payload).__name__, 'top_level_keys':list(payload)[:40] if isinstance(payload,dict) else [], 'match_count':len(matches),'match_samples':matches[:150], 'shapes':shapes,'collections':collections}

def main():
    if not PROFILE.exists(): raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın.')
    records=[]; seen=set()
    with _browser() as pw:
        ctx=pw.chromium.launch_persistent_context(str(PROFILE),headless=False)
        try:
            page=ctx.pages[0] if ctx.pages else ctx.new_page()
            def capture(response):
                u=urlsplit(response.url)
                if u.path not in PATHS: return
                key=('browser',response.url,response.status)
                if key in seen: return
                seen.add(key)
                entry={'source':'browser','path':u.path,'query_parameter_names':sorted({k for k,_ in parse_qsl(u.query)}),'status':response.status}
                if response.status==200:
                    try: entry['summary']=summarize(response.json())
                    except Exception as e: entry['parse_error_type']=type(e).__name__
                records.append(entry)
            ctx.on('response',capture)
            page.goto(BASE,wait_until='domcontentloaded',timeout=60000)
            print('Fikstür ve istatistik sayfalarını açın. 5-9 haftalarını seçip Enter basın.')
            input()
            # Query variants are diagnostics only; do not assume any variant is the correct API contract.
            variants=[{}, {'league-id':'1'}, {'leagueId':'1'}, {'league-id':'1','gameweek':'9'}, {'league-id':'1','gameweek-id':'9'}]
            for path in PATHS:
                for params in variants:
                    from urllib.parse import urlencode
                    url=BASE+path+('?' + urlencode(params) if params else '')
                    entry={'source':'request','path':path,'query_parameter_names':sorted(params)}
                    try:
                        r=ctx.request.get(url,timeout=12000)
                        entry['status']=r.status
                        if r.ok: entry['summary']=summarize(r.json())
                    except Exception as e: entry['error_type']=type(e).__name__
                    records.append(entry)
        finally: ctx.close()
    OUT.write_text(json.dumps({'classification':'API_DIAGNOSTIC_NOT_HISTORICAL_PROOF','captured_utc':datetime.now(timezone.utc).isoformat(),'requests':records,'note':'No raw response bodies, cookies, auth tokens, or user data exported. Match samples only contain club IDs and fixture metadata.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Kaydedildi:',OUT.resolve())
    for r in records: print(r['source'],r['path'],r.get('query_parameter_names'),r.get('status'),r.get('summary',{}).get('match_count',0))

if __name__=='__main__': main()
