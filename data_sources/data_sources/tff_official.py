"""Fetch official fantasy player data with a locally authenticated browser profile."""
import os
from pathlib import Path

BASE = 'https://tfffantezilig.com'
ENDPOINT = '/api/backend/projection/stats/player-stats?league-id=1'
PROFILE = Path(os.getenv('TFF_BROWSER_PROFILE', str(Path.home() / '.tff-optimizer-browser'))).expanduser()

class TFFFeedError(Exception):
    pass

def _browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise TFFFeedError('Playwright kurulu değil: pip install -r requirements.txt && python -m playwright install chromium') from exc
    return sync_playwright()

def login():
    """User logs in interactively; profile remains on their computer."""
    with _browser() as pw:
        browser = pw.chromium.launch_persistent_context(str(PROFILE), headless=False)
        try:
            browser.new_page().goto(BASE, wait_until='domcontentloaded', timeout=60000)
            input('TFF sitesine giriş yapın, ardından bu terminalde Enter tuşuna basın... ')
        finally:
            browser.close()

def _extract(payload):
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        if payload.get('error'):
            raise TFFFeedError(str(payload['error']))
        rows = next((payload[k] for k in ('players','data','results','playerStats','items') if isinstance(payload.get(k),list)), None)
        if rows is None and isinstance(payload.get('data'),dict):
            rows = next((payload['data'][k] for k in ('players','results','items') if isinstance(payload['data'].get(k),list)), None)
    else:
        rows = None
    if rows is None:
        raise TFFFeedError('API yanıt yapısı beklenenden farklı; kişisel bilgi içermeyen JSON anahtarlarını kontrol edin.')
    result=[]
    for item in rows:
        if not isinstance(item,dict) or item.get('playerId') is None: continue
        position=str(item.get('position') or '').upper()
        if position not in ('GK','DEF','MID','FWD'): continue
        result.append({'id':item['playerId'],'name':(' '.join(filter(None,[item.get('name'),item.get('surname')]))).strip() or item.get('matchName',''),
                       'match_name':item.get('matchName'), 'club_id':item.get('clubId'),
                       'team':str(item.get('clubId') or ''), 'position':position,
                       'price':item.get('cost'), 'total_points':item.get('totalPoints'),
                       'round_points':item.get('roundPoints'), 'minutes':item.get('minutes'),
                       'points_per_match':item.get('pointsPerMatch'), 'form':item.get('form'),
                       'goals':item.get('goals'), 'assists':item.get('assists'),
                       'availability_percent':item.get('availabilityPercent'),
                       'availability':item.get('availabilityStatus'), 'availability_news':item.get('availabilityNews'), 'selected_pct':item.get('selectedByPct')})
    if not result: raise TFFFeedError('Oyuncu listesi boş veya pozisyon bilgisi eksik.')
    return result

def fetch_players():
    if not PROFILE.exists():
        raise TFFFeedError('Önce terminalde python -m data_sources.tff_official login çalıştırın.')
    with _browser() as pw:
        browser = pw.chromium.launch_persistent_context(str(PROFILE), headless=True)
        try:
            response = browser.request.get(BASE+ENDPOINT, timeout=45000)
            if response.status in (401,403):
                raise TFFFeedError('Oturum geçersiz veya erişim reddedildi. Terminalde yeniden giriş yapın.')
            if not response.ok: raise TFFFeedError(f'TFF API HTTP {response.status}')
            try: payload=response.json()
            except ValueError as exc: raise TFFFeedError('API JSON döndürmedi.') from exc
            players=_extract(payload)
            return {'players':players,'count':len(players),'source':'tfffantezilig.com'}
        finally:
            browser.close()

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='login': login()
    else: print('Kullanım: python -m data_sources.tff_official login')
