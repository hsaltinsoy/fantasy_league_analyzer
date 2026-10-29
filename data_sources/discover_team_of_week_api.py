"""Discover Week Team API using the existing authenticated Playwright profile.
Never stores response bodies, cookies, tokens, or auth headers.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError
from data_sources.discover_weekly_api import safe_url, summarize

def main():
    if not PROFILE.exists():
        raise TFFFeedError("Önce python -m data_sources.tff_official login")
    rows=[]
    with _browser() as pw:
        ctx=pw.chromium.launch_persistent_context(str(PROFILE),headless=False)
        def capture(resp):
            url=safe_url(resp.url)
            if not url or '/api/' not in url or len(rows)>=250:return
            try:
                payload=resp.json()
                rows.append({'url':url,'status':resp.status,'shape':summarize(payload)})
                print('API:',url,flush=True)
            except Exception:pass
        ctx.on('response',capture)
        try:
            page=ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(BASE,wait_until='domcontentloaded',timeout=60000)
            print("Statü > Haftanın Takımı bölümünü açın; geçmiş haftalar arasında geçiş yapın.")
            input("Bittiğinde terminalde Enter'a basın...")
            page.wait_for_timeout(1500)
        finally:ctx.close()
    target=Path('tff_team_of_week_api_discovery.json')
    target.write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),
        'classification':'API_SHAPES_ONLY_NOT_VERIFIED_TEAM_OF_WEEK_DATA',
        'requests':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Kaydedildi:',target)
if __name__=='__main__':main()
