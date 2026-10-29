"""Read Football-Data style CSV files. Fixtures must be supplied explicitly."""
import csv
import io
from datetime import datetime


def parse_results(text):
    rows = []
    for row in csv.DictReader(io.StringIO(text.lstrip('\ufeff'))):
        home, away = row.get('HomeTeam'), row.get('AwayTeam')
        hg, ag = row.get('FTHG'), row.get('FTAG')
        raw_date = (row.get('Date') or '').strip()
        if not (home and away and hg and ag and raw_date):
            continue
        try:
            parsed = None
            for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
                try:
                    parsed = datetime.strptime(raw_date, fmt).date().isoformat()
                    break
                except ValueError:
                    pass
            if parsed is None:
                continue
            rows.append({'date': parsed, 'home': home.strip(), 'away': away.strip(),
                         'home_goals': int(hg), 'away_goals': int(ag)})
        except ValueError:
            continue
    return rows


def parse_fixtures(text):
    fixtures = []
    for row in csv.DictReader(io.StringIO(text.lstrip('\ufeff'))):
        home, away = (row.get('home') or row.get('HomeTeam') or '').strip(), (row.get('away') or row.get('AwayTeam') or '').strip()
        if home and away:
            fixtures.append({'home': home, 'away': away, 'date': (row.get('date') or row.get('Date') or '').strip()})
    return fixtures


def upcoming_from_results_csv(text, today=None):
    """Use future fixtures embedded in a Football-Data CSV, if present."""
    from datetime import date
    today = today or date.today()
    fixtures = parse_fixtures(text)
    future = []
    for item in fixtures:
        parsed = None
        for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
            try:
                parsed = datetime.strptime(item['date'], fmt).date()
                break
            except ValueError:
                continue
        if parsed and parsed >= today:
            future.append((parsed, item))
    if not future:
        return []
    future.sort(key=lambda item: item[0])
    # Next matchweek: upcoming matches within 7 days of the first fixture.
    first = future[0][0]
    return [dict(item, date=day.isoformat()) for day, item in future if (day - first).days <= 6]
