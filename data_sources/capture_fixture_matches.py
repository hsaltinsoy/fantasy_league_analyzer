"""Capture fixture match IDs from browser-visible API responses; no credentials exported."""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

OUT = Path('tff_fixture_matches_capture.json')
TARGET = set(range(5, 10))


def walk(node, path='', depth=0):
    if depth > 16:
        return
    if isinstance(node, dict):
        yield node, path
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from walk(value, f'{path}.{key}', depth + 1)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            if isinstance(value, (dict, list)):
                yield from walk(value, f'{path}[{i}]', depth + 1)


def extract(payload, url):
    """Return candidate match records and schema metadata, no raw responses."""
    found = []
    schemas = set()
    for obj, path in walk(payload):
        if 'homeClubId' in obj and 'awayClubId' in obj:
            home, away = obj.get('homeClubId'), obj.get('awayClubId')
            if home is None or away is None:
                continue
            week = next((obj.get(k) for k in ('gameweek', 'gameweekNumber', 'week', 'round', 'gameweekOrder') if obj.get(k) is not None), None)
            found.append({'home_club_id': str(home), 'away_club_id': str(away),
                          'match_id': str(obj['id']) if obj.get('id') is not None else None,
                          'kickoff_at': obj.get('kickoffAt'), 'week_hint': week,
                          'json_path': path, 'source_path': urlparse(url).path})
        if isinstance(obj.get('matches'), list):
            schemas.add(path + '.matches[]: ' + ', '.join(sorted({k for m in obj['matches'][:2] if isinstance(m, dict) for k in m.keys()})))
    return found, sorted(schemas)


def main():
    if not PROFILE.exists():
        raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın.')
    matches = {}
    observed = defaultdict(lambda: {'responses': 0, 'matches': 0, 'schemas': set()})
    with _browser() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE), headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def on_response(response):
            url = response.url
            if 'tfffantezilig.com/api/' not in url or 'fixture' not in url.lower():
                return
            source = urlparse(url).path
            observed[source]['responses'] += 1
            if response.status != 200:
                return
            try:
                payload = response.json()
            except Exception:
                return
            records, schemas = extract(payload, url)
            observed[source]['matches'] += len(records)
            observed[source]['schemas'].update(schemas)
            for record in records:
                key = (record['source_path'], record['match_id'], record['home_club_id'], record['away_club_id'])
                matches[key] = record

        ctx.on('response', on_response)
        page.goto(BASE, wait_until='domcontentloaded', timeout=60000)
        print('Tarayıcıda Fikstür sayfasını aç, 5-9. haftaları sırayla seç.')
        print('Bitirdiğinde buraya dönüp Enter tuşuna bas.')
        input()
        ctx.close()
    result = {'classification': 'BROWSER_CAPTURED_FIXTURES_NOT_PREDEADLINE',
              'captured_utc': datetime.now(timezone.utc).isoformat(),
              'matches': list(matches.values()),
              'endpoints': {k: {'responses': v['responses'], 'matches': v['matches'],
                                'schemas': sorted(v['schemas'])} for k, v in observed.items()},
              'note': 'Week hints may be missing. Validate match IDs and week membership before backtesting. No credentials or full API bodies exported.'}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(matches)} maç kaydı yakalandı. Dosya: {OUT.resolve()}')
    if not matches:
        print('Maç kaydı bulunamadı. endpoints alanı hangi API yanıtlarının görüldüğünü gösterecek.')


if __name__ == '__main__':
    main()
