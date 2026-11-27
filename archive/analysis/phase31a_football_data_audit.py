"""Read-only reconciliation of official fixtures, archived matches and one permitted CSV probe."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from analysis.live_benchmark import fetch_official_fixtures
from storage.db import engine_from_env
from storage.football_data_repository import FootballDataRepository, VERIFIED_TEAMS, parse_csv

SOURCE = Path('docs/phase31a_t1_source_probe.csv')
OUT = Path('docs/phase31a_football_data_audit.json')


def run():
    archive = fetch_official_fixtures()
    official = {}
    for week in range(1, 12):
        for match in archive['weeks'][str(week)]['matches']:
            if match['status'] != 'FT':
                raise ValueError(f'GW{week} is incomplete')
            official[str(match['id'])] = {'gameweek':week, 'id':match['id'],
                'date':match['kickoffAt'][:10],
                'home_id':str(match['homeClubId']), 'away_id':str(match['awayClubId']),
                'home_score':match['homeScore'], 'away_score':match['awayScore']}
    frozen = FootballDataRepository(engine_from_env()).matches_before(datetime.now(timezone.utc))
    frozen_ids = {str(m['fixture_id']) for m in frozen if m['fixture_id'] is not None}
    source = SOURCE.read_bytes()
    parsed = parse_csv(source)
    by_key = {}
    for row in parsed['rows']:
        key = (row['date'].isoformat(), VERIFIED_TEAMS.get(row['home']), VERIFIED_TEAMS.get(row['away']))
        if None in key or key in by_key:
            raise ValueError('Unmatched or duplicate CSV team/date fixture')
        by_key[key] = row
    missing = []
    for fixture_id, match in sorted(official.items(), key=lambda item:(item[1]['gameweek'], item[0])):
        if fixture_id in frozen_ids:
            continue
        key = (match['date'], match['home_id'], match['away_id'])
        row = by_key.get(key)
        same_score = bool(row and row['numbers']['FTHG'] == match['home_score'] and
                          row['numbers']['FTAG'] == match['away_score'])
        missing.append({**match, 'in_current_csv':row is not None,
            'score_matches':same_score,'csv_home':row['home'] if row else None,
            'csv_away':row['away'] if row else None,
            'csv_xg_complete':bool(row and row['numbers']['HxG'] is not None and row['numbers']['AxG'] is not None)})
    return {'official_retrieved_at':archive['captured_utc'],
        'csv_url':'https://www.football-data.co.uk/mmz4281/2627/T1.csv',
        'csv_sha256':hashlib.sha256(source).hexdigest(),
        'csv_rows':len(parsed['rows']), 'archived_rows':len(frozen),
        'official_completed_fixtures':len(official), 'missing':missing,
        'missing_in_csv':sum(not x['in_current_csv'] for x in missing),
        'mismatched_scores':sum(not x['score_matches'] for x in missing)}


if __name__ == '__main__':
    OUT.write_text(json.dumps(run(), ensure_ascii=False, indent=2), encoding='utf-8')
    print(OUT)
