"""Export only football fixture club IDs, never session secrets or full API responses."""
import json
from datetime import datetime, timezone
from pathlib import Path
from data_sources.tff_official import BASE, PROFILE, _browser, TFFFeedError

ENDPOINT = '/api/backend/fixture/leagues/1/gameweeks'
OUT = Path('tff_fixture_ids_gw5_gw9.json')


def extract(payload):
    data = payload.get('data', payload) if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        weeks = data.get('gameweeks', [])
    elif isinstance(data, list):
        weeks = data
    else:
        weeks = []
    result = {}
    for week in weeks:
        if not isinstance(week, dict):
            continue
        number = next((week[k] for k in ('gameweek', 'gameweekNumber', 'week', 'number', 'round', 'id') if isinstance(week.get(k), (int, str))), None)
        if number is None or str(number) not in {'5', '6', '7', '8', '9'}:
            continue
        matches = week.get('matches', [])
        if not isinstance(matches, list):
            continue
        extracted = []
        for match in matches:
            if not isinstance(match, dict):
                continue
            home, away = match.get('homeClubId'), match.get('awayClubId')
            if home is None or away is None:
                continue
            extracted.append({'home_club_id': str(home), 'away_club_id': str(away),
                              'kickoff_at': match.get('kickoffAt'), 'match_id': match.get('id')})
        result[str(number)] = extracted
    return result, [sorted(w.keys()) for w in weeks[:2] if isinstance(w, dict)]


def main():
    if not PROFILE.exists():
        raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın.')
    with _browser() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE), headless=False)
        try:
            response = ctx.request.get(BASE + ENDPOINT, timeout=30000)
            if not response.ok:
                raise RuntimeError(f'Fikstür API HTTP {response.status}; oturum açıp yeniden deneyin.')
            weeks, keys = extract(response.json())
        finally:
            ctx.close()
    output = {'classification': 'LIVE_API_FIXTURE_IDS_NOT_PREDEADLINE_SNAPSHOT',
              'captured_utc': datetime.now(timezone.utc).isoformat(),
              'source_endpoint': ENDPOINT, 'weeks': weeks,
              'debug_first_week_keys': keys,
              'note': 'Club IDs are directly from API. No club names or historical membership proof. No cookies exported.'}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Exported {sum(map(len, weeks.values()))} matches from {len(weeks)} weeks to {OUT.resolve()}')
    if not weeks:
        print('No weeks matched: send JSON with debug_first_week_keys for schema adjustment.')


if __name__ == '__main__':
    main()
