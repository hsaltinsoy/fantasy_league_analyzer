"""Immutable Football-Data CSV evidence, separate from official TFF results."""
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from storage import models as m

PROVIDER = 'football-data.co.uk'
SEASON = '2026-27'
# Reviewed against the 18 official TFF IDs and the 2026/27 fixture list.
VERIFIED_TEAMS = {
    'Trabzonspor': '1', 'Erzurumspor': '2', 'Kasimpasa': '3',
    'Kocaelispor': '4', 'Amedspor': '5', 'Fenerbahce': '6',
    'Konyaspor': '7', 'Corum': '8', 'Besiktas': '9', 'Goztep': '10',
    'Genclerbirligi': '11', 'Rizespor': '12', 'Buyuksehyr': '13',
    'Alanyaspor': '14', 'Samsunspor': '15', 'Eyupspor': '16',
    'Galatasaray': '17', 'Gaziantep': '18',
}
REQUIRED = {'Div', 'Date', 'HomeTeam', 'AwayTeam'}
OPTIONAL_INT = ('FTHG', 'FTAG', 'HTHG', 'HTAG', 'HS', 'AS', 'HST', 'AST',
                'HF', 'AF', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR')
OPTIONAL_FLOAT = ('HxG', 'AxG')


def _number(value, column, row_number, *, integer):
    if value is None or not value.strip():
        return None
    try:
        result = int(value) if integer else float(value)
    except ValueError as exc:
        raise ValueError(f'Row {row_number}: invalid {column}: {value!r}') from exc
    if result < 0:
        raise ValueError(f'Row {row_number}: negative {column}')
    return result


def parse_csv(raw):
    """Parse without assuming optional statistics or converting blanks to zero."""
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Football-Data CSV must be UTF-8') from exc
    reader = csv.DictReader(io.StringIO(text, newline=''))
    columns = list(reader.fieldnames or [])
    if len(columns) != len(set(columns)) or not REQUIRED.issubset(columns):
        raise ValueError(f'Invalid CSV header; required columns: {sorted(REQUIRED)}')
    rows = []
    seen = set()
    missing = Counter()
    for line_number, raw_row in enumerate(reader, 2):
        if not any(str(value or '').strip() for value in raw_row.values()):
            continue
        if None in raw_row:
            raise ValueError(f'Row {line_number}: too many CSV fields')
        row = {key: (value or '').strip() for key, value in raw_row.items()}
        if row['Div'] != 'T1':
            raise ValueError(f'Row {line_number}: unexpected division {row["Div"]!r}')
        try:
            day = datetime.strptime(row['Date'], '%d/%m/%Y').date()
        except ValueError as exc:
            raise ValueError(f'Row {line_number}: invalid date {row["Date"]!r}') from exc
        home, away = row['HomeTeam'], row['AwayTeam']
        if not home or not away or home == away:
            raise ValueError(f'Row {line_number}: missing or identical teams')
        key = (day, home, away)
        if key in seen:
            raise ValueError(f'Row {line_number}: duplicate match {key}')
        seen.add(key)
        time = None
        if row.get('Time'):
            try:
                time = datetime.strptime(row['Time'], '%H:%M').time()
            except ValueError as exc:
                raise ValueError(f'Row {line_number}: invalid time') from exc
        numbers = {column: _number(row.get(column), column, line_number, integer=True)
                   for column in OPTIONAL_INT}
        numbers.update({column: _number(row.get(column), column, line_number, integer=False)
                        for column in OPTIONAL_FLOAT})
        home_goals, away_goals = numbers['FTHG'], numbers['FTAG']
        if (home_goals is None) != (away_goals is None):
            raise ValueError(f'Row {line_number}: incomplete full-time score')
        result = row.get('FTR') or None
        if result is not None and result not in ('H', 'D', 'A'):
            raise ValueError(f'Row {line_number}: invalid full-time result')
        if home_goals is not None:
            expected = 'H' if home_goals > away_goals else 'A' if home_goals < away_goals else 'D'
            if result != expected:
                raise ValueError(f'Row {line_number}: full-time result disagrees with score')
        elif result is not None:
            raise ValueError(f'Row {line_number}: result without score')
        if numbers['HST'] is not None and numbers['HS'] is not None and numbers['HST'] > numbers['HS']:
            raise ValueError(f'Row {line_number}: home shots on target exceed shots')
        if numbers['AST'] is not None and numbers['AS'] is not None and numbers['AST'] > numbers['AS']:
            raise ValueError(f'Row {line_number}: away shots on target exceed shots')
        for column in columns:
            if not row.get(column):
                missing[column] += 1
        rows.append({'date': day, 'time': time, 'home': home, 'away': away,
                     'result': result, 'half_result': row.get('HTR') or None,
                     'numbers': numbers, 'raw': row})
    if not rows:
        raise ValueError('Football-Data CSV has no match rows')
    return {'columns': columns, 'rows': rows, 'missing': dict(missing),
            'teams': sorted({name for row in rows for name in (row['home'], row['away'])})}


class FootballDataRepository:
    def __init__(self, engine):
        self.engine = engine

    def import_file(self, path, *, season=SEASON):
        if season != SEASON:
            raise ValueError(f'Only the reviewed {SEASON} team mapping is supported')
        path = Path(path)
        raw = path.read_bytes()
        parsed = parse_csv(raw)
        digest = hashlib.sha256(raw).hexdigest()
        import_id = 'football-data:' + digest
        imported_at = datetime.now(timezone.utc)
        mapping = {name: VERIFIED_TEAMS.get(name) for name in parsed['teams']}
        unresolved = sorted(name for name, team_id in mapping.items() if team_id is None)
        inserted = skipped = linked = 0
        with self.engine.begin() as db:
            official_teams = set(db.execute(select(m.teams.c.id)).scalars())
            missing_ids = sorted(set(mapping.values()) - {None} - official_teams)
            if missing_ids:
                raise ValueError(f'Verified team IDs absent from PostgreSQL: {missing_ids}')
            old = db.execute(select(m.football_data_imports.c.season).where(
                m.football_data_imports.c.source_sha256 == digest)).scalar_one_or_none()
            if old is not None and old != season:
                raise ValueError('Identical source bytes were previously assigned another season')
            db.execute(insert(m.football_data_imports).values(
                id=import_id, provider=PROVIDER, season=season,
                original_filename=path.name, source_sha256=digest, raw_bytes=raw,
                imported_at=imported_at, row_count=len(parsed['rows']),
                metadata={'columns': parsed['columns'], 'missing': parsed['missing'],
                          'file_modified_at': datetime.fromtimestamp(path.stat().st_mtime,
                              timezone.utc).isoformat()})
                .on_conflict_do_nothing(index_elements=['id']))
            for name, team_id in mapping.items():
                if team_id is None:
                    continue
                existing = db.execute(select(m.football_data_team_mappings.c.team_id).where(
                    m.football_data_team_mappings.c.provider_name == name)).scalar_one_or_none()
                if existing is not None and existing != team_id:
                    raise ValueError(f'Conflicting verified team mapping: {name}')
                db.execute(insert(m.football_data_team_mappings).values(
                    provider_name=name, team_id=team_id,
                    verification='verified_tff_id_and_fixture_pair',
                    evidence='Reviewed 2026/27 TFF team IDs and Football-Data fixture pairs')
                    .on_conflict_do_nothing(index_elements=['provider_name']))
            fixtures = db.execute(select(m.fixtures.c.id, m.fixtures.c.home_team_id,
                m.fixtures.c.away_team_id, m.fixtures.c.kickoff_at)).all()
            by_fixture = {}
            for fixture_id, home_id, away_id, kickoff in fixtures:
                if kickoff is not None:
                    by_fixture.setdefault((kickoff.date(), home_id, away_id), []).append(fixture_id)
            for row in parsed['rows']:
                home_id, away_id = mapping[row['home']], mapping[row['away']]
                candidates = by_fixture.get((row['date'], home_id, away_id), [])
                if len(candidates) > 1:
                    raise ValueError(f'Ambiguous official fixture for {row["date"]} {row["home"]}')
                fixture_id = candidates[0] if candidates else None
                linked += fixture_id is not None
                row_sha = hashlib.sha256(json.dumps(row['raw'], sort_keys=True,
                    ensure_ascii=False).encode('utf-8')).hexdigest()
                match_id = 'football-data-match:' + hashlib.sha256((import_id +
                    row['date'].isoformat() + row['home'] + row['away']).encode()).hexdigest()
                old_hash = db.execute(select(m.football_data_matches.c.row_sha256).where(
                    m.football_data_matches.c.id == match_id)).scalar_one_or_none()
                if old_hash is not None and old_hash != row_sha:
                    raise ValueError(f'Conflicting immutable match evidence: {match_id}')
                inserted += old_hash is None
                skipped += old_hash is not None
                n = row['numbers']
                db.execute(insert(m.football_data_matches).values(
                    id=match_id, import_id=import_id, season=season,
                    match_date=row['date'], match_time=row['time'],
                    home_name=row['home'], away_name=row['away'],
                    home_team_id=home_id, away_team_id=away_id, fixture_id=fixture_id,
                    home_goals=n['FTHG'], away_goals=n['FTAG'],
                    full_time_result=row['result'], half_home_goals=n['HTHG'],
                    half_away_goals=n['HTAG'], half_time_result=row['half_result'],
                    home_xg=n['HxG'], away_xg=n['AxG'], home_shots=n['HS'],
                    away_shots=n['AS'], home_sot=n['HST'], away_sot=n['AST'],
                    raw_record=row['raw'], row_sha256=row_sha)
                    .on_conflict_do_nothing(index_elements=['id']))
        return {'provider': PROVIDER, 'season': season, 'filename': path.name,
                'source_sha256': digest, 'rows': len(parsed['rows']),
                'inserted': inserted, 'skipped': skipped,
                'teams': len(parsed['teams']), 'mapped_teams': len(mapping)-len(unresolved),
                'unmatched_teams': unresolved, 'ambiguous_teams': [],
                'linked_fixtures': linked, 'missing': parsed['missing'],
                'columns': parsed['columns']}

    def matches_before(self, cutoff):
        if cutoff.tzinfo is None:
            raise ValueError('Timezone-aware prediction cutoff required')
        with self.engine.connect() as db:
            return [dict(row) for row in db.execute(select(m.football_data_matches).join(
                m.football_data_imports,
                m.football_data_imports.c.id == m.football_data_matches.c.import_id).where(
                m.football_data_matches.c.match_date < cutoff.date(),
                m.football_data_imports.c.imported_at <= cutoff,
                m.football_data_matches.c.full_time_result.is_not(None)).order_by(
                m.football_data_matches.c.match_date,
                m.football_data_matches.c.id)).mappings()]
