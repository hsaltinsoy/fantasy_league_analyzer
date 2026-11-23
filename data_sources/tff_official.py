"""Fetch official fantasy player data with a locally authenticated browser profile."""
import os
from pathlib import Path

BASE = 'https://tfffantezilig.com'
ENDPOINT = '/api/backend/projection/stats/player-stats?league-id=1'
HISTORY_ENDPOINT = '/api/backend/projection/stats/players/{player_id}/history?league-id=1'
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

def fetch_players(*, include_evidence=False):
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
            result = {'players':players,'count':len(players),'source':'tfffantezilig.com'}
            if include_evidence:
                from datetime import datetime, timezone
                result.update(raw_payload=payload, retrieved_at=datetime.now(timezone.utc),
                              source_url=BASE+ENDPOINT)
            return result
        finally:
            browser.close()


def fetch_player_histories(player_ids, *, completed_through, target_week,
                           min_interval_seconds=0, max_retries=0,
                           continue_on_error=False, include_metrics=False,
                           progress=None):
    """Read official weekly rows once, retaining only completed prior gameweeks."""
    from datetime import datetime, timezone
    from collections import Counter
    from time import monotonic, sleep
    if completed_through >= target_week or completed_through < 1:
        raise ValueError('Completed week must precede target week')
    if not PROFILE.exists():
        raise TFFFeedError('TFF browser profile is missing')
    result = {}
    metrics = {'requests': 0, 'successful_requests': 0, 'failed_requests': 0,
               'retries': 0, 'errors': {}, 'raw_week_coverage': {},
               'inconsistent_records': {}, 'concurrency': 1}
    raw_weeks = Counter()
    started = monotonic()
    last_request = None
    with _browser() as pw:
        browser = pw.chromium.launch_persistent_context(str(PROFILE), headless=True)
        try:
            for pid in sorted({str(pid) for pid in player_ids}, key=int):
                rows = None
                for attempt in range(max_retries + 1):
                    if last_request is not None:
                        sleep(max(0, min_interval_seconds - (monotonic() - last_request)))
                    last_request = monotonic()
                    metrics['requests'] += 1
                    try:
                        response = browser.request.get(BASE + HISTORY_ENDPOINT.format(player_id=pid),
                                                       timeout=45000)
                        if response.status in (401, 403, 429):
                            raise TFFFeedError(f'Official player history HTTP {response.status} for {pid}')
                        if not response.ok:
                            raise TFFFeedError(f'Official player history HTTP {response.status} for {pid}')
                        payload = response.json()
                        rows = payload.get('data', payload) if isinstance(payload, dict) else payload
                        if not isinstance(rows, list):
                            raise TFFFeedError(f'Invalid official player history for {pid}')
                        metrics['successful_requests'] += 1
                        break
                    except Exception as exc:
                        retryable = not isinstance(exc, TFFFeedError) or 'HTTP 5' in str(exc)
                        if attempt < max_retries and retryable:
                            metrics['retries'] += 1
                            continue
                        metrics['failed_requests'] += 1
                        metrics['errors'][pid] = str(exc)
                        if not continue_on_error or 'HTTP 401' in str(exc) or 'HTTP 403' in str(exc) or 'HTTP 429' in str(exc):
                            raise
                if rows is None:
                    result[pid] = []
                    if progress:
                        progress(len(result), len(player_ids), metrics)
                    continue
                valid = []
                seen = set()
                for row in rows:
                    if not isinstance(row, dict) or not str(row.get('gameweekOrder', '')).isdigit():
                        metrics['inconsistent_records'][pid] = metrics['inconsistent_records'].get(pid, 0) + 1
                        continue
                    week = int(row['gameweekOrder'])
                    raw_weeks[week] += 1
                    if week > completed_through:
                        continue
                    if week in seen:
                        if not continue_on_error:
                            raise TFFFeedError(f'Duplicate history week {week} for {pid}')
                        metrics['inconsistent_records'][pid] = metrics['inconsistent_records'].get(pid, 0) + 1
                        continue
                    seen.add(week)
                    valid.append(row)
                result[pid] = sorted(valid, key=lambda row: int(row['gameweekOrder']))
                if progress:
                    progress(len(result), len(player_ids), metrics)
        finally:
            browser.close()
    output = {'rows_by_player': result, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'source_url': BASE + HISTORY_ENDPOINT}
    if include_metrics:
        metrics['elapsed_seconds'] = round(monotonic() - started, 3)
        metrics['requests_per_second'] = round(metrics['requests'] / max(metrics['elapsed_seconds'], .001), 3)
        metrics['raw_week_coverage'] = dict(sorted(raw_weeks.items()))
        output['metrics'] = metrics
    return output

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='login': login()
    else: print('Kullanım: python -m data_sources.tff_official login')
