"""Official club metadata for readable fixture labels; safe local fallback."""
import json
from pathlib import Path
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

ENDPOINT='/api/backend/projection/stats/club-stats?league-id=1'
CACHE=Path('historical_data/club_metadata.json')

def load_clubs(live=False):
    if live:
        try:
            if not PROFILE.exists(): raise TFFFeedError('TFF oturumu bulunamadı')
            with _browser() as pw:
                context=pw.chromium.launch_persistent_context(str(PROFILE),headless=True)
                try:
                    response=context.request.get(BASE+ENDPOINT,timeout=30000)
                    if not response.ok:raise TFFFeedError(f'Club API HTTP {response.status}')
                    payload=response.json()
                finally:context.close()
            clubs=payload.get('data',[])
            if not isinstance(clubs,list) or len(clubs)<10:raise ValueError('Kulüp listesi eksik')
            result={str(c['id']):{'name':c.get('name') or c.get('shortName') or str(c['id']),
                   'short_name':c.get('shortName') or c.get('abbreviation') or c.get('name') or str(c['id']),
                   'logo_url':c.get('logoUrl') if str(c.get('logoUrl') or '').startswith('https://') else None}
                    for c in clubs if isinstance(c,dict) and c.get('id') is not None}
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            return result
        except Exception:
            pass
    if CACHE.exists():
        try:return json.loads(CACHE.read_text(encoding='utf-8'))
        except (OSError,ValueError):pass
    return {}
