"""Export fantasy league fixtures grouped by actual gameweek order (not inferred dates)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

OUT = Path('tff_fixtures_verified_v5.json')
ENDPOINT = '/api/backend/projection/stats/fixtures?league-id=1'

def main():
    if not PROFILE.exists():
        raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın.')
    with _browser() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE), headless=True)
        try:
            response = ctx.request.get(BASE + ENDPOINT, timeout=30000)
            if not response.ok:
                raise RuntimeError(f'Fixture API HTTP {response.status}')
            payload = response.json()
        finally:
            ctx.close()
    data = payload.get('data') if isinstance(payload, dict) else None
    weeks = data.get('gameweeks') if isinstance(data, dict) else None
    if not isinstance(weeks, list):
        raise RuntimeError('Beklenen data.gameweeks listesi bulunamadı')
    result = {}
    for week in weeks:
        if not isinstance(week, dict):
            continue
        order = week.get('order')
        if order is None:
            raise RuntimeError('Bir gameweek içinde order yok')
        matches = week.get('matches')
        if not isinstance(matches, list):
            raise RuntimeError(f'Hafta {order}: matches listesi yok')
        clean = []
        for m in matches:
            if not isinstance(m, dict) or m.get('homeClubId') is None or m.get('awayClubId') is None:
                raise RuntimeError(f'Hafta {order}: eksik maç ID alanları')
            clean.append({k:m.get(k) for k in ('id','homeClubId','awayClubId','kickoffAt','homeScore','awayScore','status')})
        key = str(order)
        if key in result:
            raise RuntimeError(f'Tekrarlanan gameweek order: {order}')
        result[key] = {'gameweek_id':week.get('id'), 'deadline':week.get('deadline'), 'matches':clean}
    count = sum(len(v['matches']) for v in result.values())
    if count != 306 or len(result) != 34:
        print(f'Uyarı: Önceki tanılamada 34 hafta/306 maç vardı; şimdi {len(result)} hafta/{count} maç.')
    output = {'classification':'LIVE_API_FIXTURES_NOT_PREDEADLINE_SNAPSHOT', 'captured_utc':datetime.now(timezone.utc).isoformat(), 'source_endpoint':ENDPOINT, 'gameweek_count':len(result), 'match_count':count, 'weeks':result, 'note':'Club names not verified; API current snapshot, not historical pre-deadline data.'}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Kaydedildi: {OUT.resolve()} | {len(result)} hafta | {count} maç')
    for k in ('5','6','7','8','9'):
        print(f'Hafta {k}: {len(result.get(k,{}).get("matches",[]))} maç')

if __name__ == '__main__':
    main()
