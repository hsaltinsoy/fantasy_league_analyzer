"""Optional independent fixture coverage from football-data.co.uk (no credentials).

Only scheduled matches within the selected round's date window are considered.
No fixtures are fabricated when the provider is unavailable.
"""
import csv
import io
from datetime import datetime, timedelta
import requests
from data_sources.team_names import normalize_team


def supplement(fixtures, season, get=requests.get):
    if not fixtures:
        return fixtures, ['No primary fixtures to anchor the round.']
    dates = [datetime.strptime(m['date'][:10], '%Y-%m-%d').date() for m in fixtures]
    start, end = min(dates) - timedelta(days=1), max(dates) + timedelta(days=1)
    url = f'https://www.football-data.co.uk/mmz4281/{season}/T1.csv'
    try:
        response = get(url, timeout=12, headers={'User-Agent': 'PersonalFantasyOptimizer/1.8'})
        response.raise_for_status()
        rows = csv.DictReader(io.StringIO(response.content.decode('utf-8-sig')))
        additions = []
        for row in rows:
            if not row.get('HomeTeam') or not row.get('AwayTeam') or not row.get('Date'):
                continue
            parsed = None
            for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
                try:
                    parsed = datetime.strptime(row['Date'].strip(), fmt).date()
                    break
                except ValueError:
                    pass
            if parsed is None or not start <= parsed <= end:
                continue
            additions.append({'date': parsed.isoformat(), 'home': row['HomeTeam'], 'away': row['AwayTeam']})
    except (requests.RequestException, UnicodeError, csv.Error) as exc:
        return fixtures, [f'Supplementary fixture feed unavailable: {type(exc).__name__}']
    # Reject conflicting fixtures. A team must appear at most once in a round.
    merged = list(fixtures)
    occupied = {normalize_team(t) for m in merged for t in (m['home'], m['away'])}
    count = 0
    for m in additions:
        a, b = normalize_team(m['home']), normalize_team(m['away'])
        if not a or not b or a == b or a in occupied or b in occupied:
            continue
        merged.append(m)
        occupied.update((a, b))
        count += 1
    return merged, [f'Supplementary source added {count} fixtures; verify the season and round if coverage is incomplete.']
