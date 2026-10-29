"""Discover the TFF player-history JSON endpoint using your existing local login.

Run: python -m data_sources.discover_weekly_api
Open one player's detail and click their weekly-points chart. Press Enter in
terminal to save a redacted report. No cookies, tokens or response bodies saved.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

SENSITIVE = re.compile(r'auth|token|session|secret|key|cookie|password|email|phone', re.I)

def safe_url(url):
    parts = urlsplit(url)
    if parts.hostname not in ('tfffantezilig.com', 'www.tfffantezilig.com'):
        return None
    params = [(k, '[REDACTED]' if SENSITIVE.search(k) else v) for k,v in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), ''))

def summarize(payload):
    if isinstance(payload, dict):
        keys = [str(k) for k in payload if not SENSITIVE.search(str(k))]
        return {'type':'object', 'keys': keys[:40], 'nested': {k: summarize(payload[k]) for k in keys[:10] if isinstance(payload[k], (list,dict))}}
    if isinstance(payload, list):
        return {'type':'array','length':len(payload), 'first':summarize(payload[0]) if payload and isinstance(payload[0],(dict,list)) else 'scalar/empty'}
    return {'type':type(payload).__name__}

def main():
    if not PROFILE.exists():
        raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın.')
    records=[]
    diagnostics={'responses_seen':0,'tff_responses':0,'json_responses':0,'errors':[]}
    with _browser() as pw:
        browser=pw.chromium.launch_persistent_context(str(PROFILE),headless=False)
        def handle(response):
            diagnostics['responses_seen']+=1
            url=safe_url(response.url)
            if not url: return
            diagnostics['tff_responses']+=1
            if len(records)>=250:return
            ct=response.headers.get('content-type','')
            # Some endpoints return JSON with text/plain or no content-type.
            if not ('json' in ct or '/api/' in response.url or '/graphql' in response.url):return
            try:
                payload=response.json()
                diagnostics['json_responses']+=1
                records.append({'url':url,'status':response.status,'shape':summarize(payload)})
                print('Yakalandi:',url,flush=True)
            except Exception as e:
                if len(diagnostics['errors'])<8:
                    diagnostics['errors'].append({'url':url,'error_type':type(e).__name__})
        browser.on('response',handle)
        try:
            page=browser.pages[0] if browser.pages else browser.new_page()
            page.goto(BASE,wait_until='domcontentloaded',timeout=60000)
            page.wait_for_timeout(3000)
            print('Oyuncu detayini acin, hafta puanlarini goruntuleyin ve mumkunse baska haftaya gecin.')
            input('Isiniz bitince Enter tusuna basin... ')
            page.wait_for_timeout(3000)  # let in-flight response events finish
        finally:
            browser.close()
    output=Path('tff_weekly_api_discovery.json')
    output.write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'requests':records,'diagnostics':diagnostics},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(records)} JSON yaniti kaydedildi. TFF yanitlari: {diagnostics["tff_responses"]}. Dosya: {output.resolve()}')
    print('Paylasmadan once dosyada hassas bilgi olmadigini kontrol edin.')

if __name__=='__main__': main()
