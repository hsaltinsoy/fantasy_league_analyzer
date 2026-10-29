"""Collect official retrospective evidence without touching live prediction records."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from data_sources.tff_official import BASE, ENDPOINT as PLAYER_ENDPOINT, PROFILE, _browser, TFFFeedError
from data_sources.team_of_week import ENDPOINT as DREAM_ENDPOINT, parse as parse_dream

OUTPUT = Path('historical_data/recovered')
FIXTURE_ENDPOINT = '/api/backend/projection/stats/fixtures?league-id=1'
CLUB_ENDPOINT = '/api/backend/projection/stats/club-stats?league-id=1'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _save_raw(payload, label, url, retrieved_at, output):
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')
    digest = hashlib.sha256(encoded).hexdigest()
    path = Path(output) / 'raw' / 'official' / f'{label}_{digest[:16]}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(encoded)
    return {'url': url, 'retrieved_at': retrieved_at, 'sha256': digest,
            'relative_path': str(path.relative_to(output)).replace('\\', '/'),
            'evidence_quality': 'official_api_retrospective_retrieval_not_deadline_verified'}


def collect_official(output=OUTPUT, weeks=range(1, 10), interval_seconds=.4):
    """One authorized browser session; sequential, paced, read-only GETs."""
    output = Path(output)
    if not PROFILE.exists():
        raise TFFFeedError('Existing authorized TFF browser profile is unavailable')
    if interval_seconds < .2:
        raise ValueError('Collection interval must be at least 0.2 seconds')
    weeks = tuple(weeks)
    if len(set(weeks)) != len(weeks) or any(not isinstance(w, int) or w < 1 for w in weeks):
        raise ValueError('Gameweeks must be unique positive integers')
    requests = [('player_stats_current', BASE + PLAYER_ENDPOINT, None),
                ('fixtures_current', BASE + FIXTURE_ENDPOINT, None),
                ('clubs_current', BASE + CLUB_ENDPOINT, None)]
    requests.extend((f'dream_team_gw{week}', BASE + DREAM_ENDPOINT.format(week=week), week)
                    for week in weeks)
    entries, errors = {}, {}
    with _browser() as pw:
        context = pw.chromium.launch_persistent_context(str(PROFILE), headless=True)
        try:
            for index, (label, url, week) in enumerate(requests):
                if index:
                    time.sleep(interval_seconds)
                response = context.request.get(url, timeout=45000)
                retrieved_at = _now()
                if response.status in (401, 403, 429):
                    raise TFFFeedError(f'TFF API HTTP {response.status}; collection stopped')
                if not response.ok:
                    errors[label] = f'HTTP {response.status}'
                    continue
                payload = response.json()
                if week is not None:
                    try:
                        parsed = parse_dream(payload, week)
                        if parsed['source_gameweek_id'] != week:
                            raise ValueError('Dream-team gameweek ID mismatch')
                    except (KeyError, ValueError) as exc:
                        errors[label] = str(exc)
                        continue
                entries[label] = _save_raw(payload, label, url, retrieved_at, output)
                if week is not None:
                    entries[label]['effective_gameweek'] = week
        finally:
            context.close()
    manifest = {'classification': 'retrospective_collection_not_predeadline_verified',
                'collected_at': _now(), 'entries': entries, 'errors': errors,
                'limitations': ['Current player list is not a historical position, club, price or availability snapshot.',
                                'Historical dream-team positions are observed only for selected players.',
                                'No local capture timestamp proves what was visible at an old deadline.']}
    manifest_path = output / 'official_collection_manifest.json'
    if manifest_path.exists():
        archived = output / f'official_collection_manifest_{hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:16]}.json'
        if not archived.exists():
            archived.write_bytes(manifest_path.read_bytes())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description='Collect retrospective official TFF player, fixture and dream-team data')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--interval', type=float, default=.4)
    args = parser.parse_args()
    result = collect_official(args.output, interval_seconds=args.interval)
    print(json.dumps({'saved': list(result['entries']), 'errors': result['errors'],
                      'classification': result['classification']}, indent=2))


if __name__ == '__main__':
    main()
