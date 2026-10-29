"""Normalize staged TFF evidence without reading files or changing runtime storage."""
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from storage.db import engine_from_env
from storage import models as m

ROOT = 'historical_data/'
RECOVERED = ROOT + 'recovered/'
HISTORY = re.compile(r'^historical_data/player_(\d+)\.json$')
POSITIONS = {'GK', 'DEF', 'MID', 'FWD'}


def digest(value):
    if isinstance(value, bytes):
        raw = value
    else:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                         allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        result = Decimal(str(value))
    except Exception:
        return None
    if not result.is_finite() or (positive and result <= 0):
        return None
    return result


def integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def artifact(db, path, expected_hash=None):
    query = select(m.source_artifacts).where(m.source_artifacts.c.source_path == path)
    if expected_hash:
        query = query.where(m.source_artifacts.c.content_sha256 == expected_hash)
    rows = db.execute(query).mappings().all()
    if len(rows) != 1:
        raise ValueError(f'Expected one staged artifact for {path}; found {len(rows)}')
    row = dict(rows[0])
    if digest(row['raw_bytes']) != row['content_sha256']:
        raise ValueError(f'Staged artifact hash mismatch: {path}')
    return row


def parsed(row):
    try:
        return json.loads(row['raw_bytes'].decode('utf-8-sig'))
    except (UnicodeError, ValueError) as exc:
        raise ValueError(f'Invalid staged JSON: {row["source_path"]}') from exc


def _equal(a, b):
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        return a is None and b is None or a is not None and b is not None and Decimal(str(a)) == Decimal(str(b))
    return a == b


class Importer:
    def __init__(self, db):
        self.db = db
        self.counts = defaultdict(Counter)
        self.conflicts = []
        self.unresolved = []

    def put(self, table, key, values):
        query = select(table).where(*(table.c[field] == value for field, value in key.items()))
        current = self.db.execute(query).mappings().first()
        if current is None:
            self.db.execute(pg_insert(table).values(**values).on_conflict_do_nothing())
            current = self.db.execute(query).mappings().first()
            if current is None:
                raise RuntimeError(f'Insert failed: {table.name} {key}')
            state = 'inserted'
        else:
            state = 'skipped'
        differing = [field for field, value in values.items() if not _equal(current[field], value)]
        if differing:
            state = 'conflicting'
            self.conflicts.append({'table': table.name, 'key': key, 'fields': differing})
        self.counts[table.name][state] += 1
        return state

    def evidence(self, row, source_id, *, source_url=None, quality=None, retrieved_at=None):
        sha = row['content_sha256']
        payload_id = digest(row['source_path'] + ':' + sha)
        retrieved = retrieved_at or row['source_retrieved_at'] or row['imported_at']
        known = retrieved_at is not None or row['source_retrieved_at'] is not None
        run_id = 'artifact:' + payload_id
        self.put(m.collection_runs, {'id': run_id}, dict(
            id=run_id, source_id=source_id, retrieved_at=retrieved, status='imported',
            content_hash=sha, error=None,
            metadata={'artifact_path': row['source_path'], 'source_url': source_url,
                      'retrieval_time_from_source': known}))
        self.put(m.source_payloads, {'id': payload_id}, dict(
            id=payload_id, run_id=run_id, source_path=row['source_path'], content_sha256=sha,
            raw_payload=parsed(row), raw_text=None,
            retrieved_at=retrieved if known else None, evidence_quality=quality))
        return payload_id, retrieved, known


def _manifest_artifact(db, manifest, label):
    entry = manifest['entries'][label]
    row = artifact(db, RECOVERED + entry['relative_path'].replace('\\', '/'), entry['sha256'])
    return row, entry


def normalize(engine):
    """One transaction. Same-source conflicts are reported and never overwritten."""
    with engine.begin() as db:
        db.execute(select(func.pg_advisory_xact_lock(170018)))
        work = Importer(db)
        manifest_row = artifact(db, RECOVERED + 'official_collection_manifest.json')
        manifest = parsed(manifest_row)
        coverage_row = artifact(db, RECOVERED + 'coverage_report.json')
        coverage = parsed(coverage_row)
        if manifest.get('classification') != 'retrospective_collection_not_predeadline_verified':
            raise ValueError('Unexpected official recovery manifest classification')
        source_defs = (
            ('tff_official', 'TFF Fantasy official API', 'https://tfffantezilig.com/api/backend/', 'official'),
            ('local_tff_history', 'Local archive of TFF player history responses',
             'https://tfffantezilig.com/api/backend/projection/stats/players/{player_id}/history?league-id=1',
             'official_origin_retrieval_time_unknown'),
            ('derived_recovery', 'Retrospective position and club reconstruction', None, 'derived'),
            ('local_fixture_archive', 'Locally verified fixture archive', None, 'derived'))
        for sid, name, url, kind in source_defs:
            work.put(m.data_sources, {'id': sid}, dict(id=sid, name=name, url=url, kind=kind, metadata=None))
        work.evidence(manifest_row, 'derived_recovery', quality=manifest['classification'],
                      retrieved_at=timestamp(manifest.get('collected_at')))
        work.evidence(coverage_row, 'derived_recovery', quality=coverage.get('classification'),
                      retrieved_at=timestamp(coverage.get('generated_at')))

        official = {}
        for label in ('clubs_current', 'player_stats_current', 'fixtures_current'):
            row, entry = _manifest_artifact(db, manifest, label)
            if entry['sha256'] != row['content_sha256']:
                raise ValueError(f'Manifest checksum mismatch for {label}')
            quality = entry.get('evidence_quality') or 'official_retrieved_retrospectively'
            evidence_id, _, _ = work.evidence(row, 'tff_official', source_url=entry.get('url'), quality=quality,
                                              retrieved_at=timestamp(entry.get('retrieved_at')))
            official[label] = (row, parsed(row), entry, evidence_id)

        club_row, club_payload, _, club_evidence_id = official['clubs_current']
        club_ids = set()
        for club in club_payload.get('data') or []:
            cid = club.get('id')
            if integer(cid) is None or not club.get('name') or cid in club_ids:
                raise ValueError('Duplicate or invalid official club ID')
            club_ids.add(cid)
            work.put(m.teams, {'id': str(cid)}, dict(id=str(cid), name=club['name'],
                source_id='tff_official', metadata={'source_payload_id': club_evidence_id,
                                                   'source_row_sha256': digest(club)}))

        roster_row, roster_payload, roster_entry, roster_evidence_id = official['player_stats_current']
        roster_retrieved = timestamp(roster_entry.get('retrieved_at')) or roster_row['imported_at']
        roster_ids = set()
        for player in roster_payload.get('data') or []:
            pid = player.get('playerId')
            if integer(pid) is None or pid in roster_ids:
                raise ValueError('Duplicate or invalid official player ID')
            roster_ids.add(pid)
            name = ' '.join(str(player.get(key) or '').strip() for key in ('name', 'surname')).strip()
            if not name:
                raise ValueError(f'Official player {pid} has no name')
            work.put(m.players, {'id': str(pid)}, dict(id=str(pid), name=name,
                source_id='tff_official', metadata={'source_payload_id': roster_evidence_id,
                                                   'source_row_sha256': digest(player)}))
            club = player.get('clubId')
            if club is not None and club not in club_ids:
                work.unresolved.append({'kind': 'current_club', 'player_id': pid, 'club_id': club})
            position = player.get('position') if player.get('position') in POSITIONS else None
            state_id = f'current:{pid}:{roster_row["content_sha256"][:16]}'
            work.put(m.player_state, {'id': state_id}, dict(
                id=state_id, player_id=str(pid), gameweek_id=None, effective_gameweek=None,
                team_id=str(club) if club in club_ids else None, position=position,
                price=number(player.get('cost'), positive=True),
                availability=player.get('availabilityStatus') if isinstance(player.get('availabilityStatus'), str) else None,
                suspension=None, effective_at=None, retrieved_at=roster_retrieved,
                evidence_quality='official_current_roster_retrieved_after_historical_deadlines',
                source_payload_id=roster_evidence_id,
                metadata={'state_kind': 'current_roster', 'source_row_sha256': digest(player),
                          'historical_deadline_proof': False}))
            work.put(m.player_identity_mappings, {'id': f'tff:{pid}'}, dict(
                id=f'tff:{pid}', player_id=str(pid), provider='tff', provider_player_id=str(pid),
                name_alias=None, confidence='verified', version='stable_official_tff_id',
                valid_from=None, valid_to=None, evidence_id=roster_evidence_id))
            work.put(m.identity_reviews, {'id': f'xgedge:unlinked:{pid}'}, dict(
                id=f'xgedge:unlinked:{pid}', player_id=str(pid), provider='xgedge',
                provider_player_id=None, provider_name=None,
                reason='No persistent verified xgEdge provider ID in staged crosswalk',
                confidence='unmatched', source_payload_id=roster_evidence_id,
                candidate_ids=None, status='open'))

        fixtures_row, fixtures_payload, fixture_entry, fixtures_evidence_id = official['fixtures_current']
        fixture_weeks = fixtures_payload.get('data', {}).get('gameweeks') or []
        seen_weeks, seen_fixture_ids = set(), set()
        fixture_index = defaultdict(list)
        for week in fixture_weeks:
            order, official_id = week.get('order'), week.get('id')
            if integer(order) is None or order < 1 or integer(official_id) is None or order in seen_weeks:
                raise ValueError('Duplicate or invalid official gameweek')
            seen_weeks.add(order)
            work.put(m.gameweeks, {'id': order}, dict(
                id=order, official_id=str(official_id), deadline_at=timestamp(week.get('deadline')),
                deadline_source_id='tff_official',
                deadline_retrieved_at=timestamp(fixture_entry.get('retrieved_at')),
                metadata={'source_payload_id': fixtures_evidence_id,
                          'source_row_sha256': digest(week),
                          'classification': 'official_retrieved_retrospectively_not_predeadline_verified'}))
            for match in week.get('matches') or []:
                fid, home, away = match.get('id'), match.get('homeClubId'), match.get('awayClubId')
                if integer(fid) is None or fid in seen_fixture_ids or home not in club_ids or away not in club_ids or home == away:
                    raise ValueError(f'Duplicate or invalid official fixture {fid}')
                seen_fixture_ids.add(fid)
                fixture_index[(order, 'H', str(away))].append((fid, home))
                fixture_index[(order, 'A', str(home))].append((fid, away))
                work.put(m.fixtures, {'id': str(fid)}, dict(
                    id=str(fid), gameweek_id=order, home_team_id=str(home), away_team_id=str(away),
                    kickoff_at=timestamp(match.get('kickoffAt')), status=match.get('status'),
                    source_payload_id=fixtures_evidence_id))
                work.put(m.fixture_observations, {'id': f'official:{fid}:{fixtures_row["content_sha256"][:16]}'}, dict(
                    id=f'official:{fid}:{fixtures_row["content_sha256"][:16]}', fixture_id=str(fid),
                    source_payload_id=fixtures_evidence_id, gameweek_id=order,
                    home_team_id=str(home), away_team_id=str(away), status=match.get('status'),
                    home_score=integer(match.get('homeScore')), away_score=integer(match.get('awayScore')),
                    source_quality='official_fixture_response_retrieved_retrospectively',
                    metadata={'source_row_sha256': digest(match)}))
                if match.get('status') == 'FT' and integer(match.get('homeScore')) is not None and integer(match.get('awayScore')) is not None:
                    work.put(m.match_results, {'fixture_id': str(fid)}, dict(
                        fixture_id=str(fid), home_score=match['homeScore'], away_score=match['awayScore'],
                        completed_at=None, source_payload_id=fixtures_evidence_id))

        # A second fixture archive is retained as source-specific observations.
        local_fixture = artifact(db, ROOT + 'tff_fixtures_verified_v5.json')
        local_payload_id, _, _ = work.evidence(local_fixture, 'local_fixture_archive',
            quality='locally_verified_fixture_archive_not_independent_deadline_proof',
            retrieved_at=timestamp(parsed(local_fixture).get('captured_utc')))
        for week_text, data in (parsed(local_fixture).get('weeks') or {}).items():
            week = int(week_text)
            for match in data.get('matches') or []:
                fid = str(match.get('id'))
                if fid not in {str(value) for value in seen_fixture_ids}:
                    work.unresolved.append({'kind': 'local_fixture_missing_official_id', 'fixture_id': fid})
                    continue
                obs_id = f'local:{fid}:{local_payload_id[:16]}'
                work.put(m.fixture_observations, {'id': obs_id}, dict(
                    id=obs_id, fixture_id=fid, source_payload_id=local_payload_id,
                    gameweek_id=week, home_team_id=str(match.get('homeClubId')) if match.get('homeClubId') is not None else None,
                    away_team_id=str(match.get('awayClubId')) if match.get('awayClubId') is not None else None,
                    status=match.get('status'), home_score=integer(match.get('homeScore')),
                    away_score=integer(match.get('awayScore')),
                    source_quality='local_fixture_archive_retrospective',
                    metadata={'source_row_sha256': digest(match)}))

        # Player histories have no independently captured retrieval timestamp.
        history_artifacts = db.execute(select(m.source_artifacts).where(
            m.source_artifacts.c.source_path.like(ROOT + 'player_%.json'))).mappings().all()
        history_paths = defaultdict(list)
        for row in history_artifacts:
            found = HISTORY.fullmatch(row['source_path'])
            if found:
                history_paths[found.group(1)].append(dict(row))
        for pid, versions in sorted(history_paths.items(), key=lambda item: int(item[0])):
            if len(versions) != 1:
                raise ValueError(f'Multiple staged versions of player history {pid}; select evidence explicitly')
            row = versions[0]
            if int(pid) not in roster_ids:
                work.unresolved.append({'kind': 'history_player_missing_official_roster', 'player_id': pid})
                continue
            history = parsed(row)
            if not isinstance(history, list):
                raise ValueError(f'History is not a list for player {pid}')
            evidence_id, retrieved_at, _ = work.evidence(row, 'local_tff_history',
                source_url=f'https://tfffantezilig.com/api/backend/projection/stats/players/{pid}/history?league-id=1',
                quality='local_tff_history_archive_retrieval_time_unknown')
            seen_player_weeks = set()
            for index, result in enumerate(history):
                if not isinstance(result, dict):
                    raise ValueError(f'Invalid history result for {pid} at index {index}')
                week = result.get('gameweekOrder')
                if integer(week) is None or week not in seen_weeks or week in seen_player_weeks:
                    raise ValueError(f'Duplicate or invalid player-week {pid}/{week}')
                seen_player_weeks.add(week)
                official_week_id = next(w['id'] for w in fixture_weeks if w['order'] == week)
                if result.get('gameweekId') != official_week_id:
                    raise ValueError(f'Official gameweek ID mismatch for {pid}/{week}')
                candidates = fixture_index.get((week, result.get('homeAway'), str(result.get('opponentClubId'))), [])
                fid, own_club = candidates[0] if len(candidates) == 1 else (None, None)
                if fid is None:
                    work.unresolved.append({'kind': 'fixture_mapping', 'player_id': pid,
                                            'gameweek': week, 'candidate_count': len(candidates)})
                points = number(result.get('points'))
                minutes = integer(result.get('minutesPlayed'))
                if minutes is not None and minutes < 0:
                    raise ValueError(f'Negative minutes for {pid}/{week}')
                row_hash = digest(result)
                obs_id = digest(f'{evidence_id}:{pid}:{week}:{index}')
                work.put(m.stat_observations, {'id': obs_id}, dict(
                    id=obs_id, player_id=pid, gameweek_id=week,
                    fixture_id=str(fid) if fid is not None else None,
                    source_payload_id=evidence_id, fantasy_points=points, minutes=minutes,
                    goals=integer(result.get('goals')), assists=integer(result.get('assists')),
                    source_quality='local_tff_history_archive_retrieval_time_unknown',
                    metadata={'source_row_sha256': row_hash, 'source_row_index': index,
                              'opponent_club_id': result.get('opponentClubId'),
                              'home_away': result.get('homeAway'),
                              'appeared': minutes > 0 if minutes is not None else None,
                              'xg_xa_placeholder_not_imported': True}))
                if fid is not None:
                    work.put(m.player_gameweek_stats,
                        {'player_id': pid, 'gameweek_id': week, 'fixture_id': str(fid)}, dict(
                            player_id=pid, gameweek_id=week, fixture_id=str(fid),
                            minutes=minutes, fantasy_points=points,
                            goals=integer(result.get('goals')), assists=integer(result.get('assists')),
                            source_payload_id=evidence_id,
                            metadata={'source_row_sha256': row_hash, 'source_row_index': index,
                                      'appeared': minutes > 0 if minutes is not None else None,
                                      'xg_xa_placeholder_not_imported': True}))
                    state_id = f'postmatch:{pid}:{week}:{evidence_id[:16]}'
                    work.put(m.player_state, {'id': state_id}, dict(
                        id=state_id, player_id=pid, gameweek_id=week, effective_gameweek=week,
                        team_id=str(own_club), position=None,
                        price=number(result.get('cost'), positive=True), availability=None,
                        suspension=None, effective_at=None, retrieved_at=retrieved_at,
                        evidence_quality='postmatch_club_and_price_not_deadline_state',
                        source_payload_id=evidence_id,
                        metadata={'state_kind': 'postmatch_history', 'source_row_sha256': row_hash,
                                  'historical_deadline_proof': False}))

        position_info = coverage.get('position_evidence') or {}
        pos_row = artifact(db, RECOVERED + position_info['path'], position_info['sha256'])
        pos_payload = parsed(pos_row)
        pos_evidence_id, _, _ = work.evidence(pos_row, 'derived_recovery',
            quality=pos_payload.get('classification'))
        for pid, entries in (pos_payload.get('players') or {}).items():
            if int(pid) not in roster_ids:
                work.unresolved.append({'kind': 'position_player_missing_official_roster', 'player_id': pid})
                continue
            for index, entry in enumerate(entries):
                week = entry.get('effective_gameweek')
                if integer(week) is None or week < 0 or (week and week not in seen_weeks):
                    work.unresolved.append({'kind': 'invalid_position_week', 'player_id': pid, 'week': week})
                    continue
                position = entry.get('position') if entry.get('position') in POSITIONS else None
                club = entry.get('club_id')
                club_id = str(club) if club is not None else None
                valid_club = club_id is not None and club_id in {str(value) for value in club_ids}
                if club is not None and not valid_club:
                    work.unresolved.append({'kind': 'position_club_missing', 'player_id': pid, 'club_id': club})
                state_id = f'position:{pid}:{week}:{index}:{pos_evidence_id[:16]}'
                work.put(m.player_state, {'id': state_id}, dict(
                    id=state_id, player_id=pid, gameweek_id=week if week else None,
                    effective_gameweek=week, team_id=club_id if valid_club else None,
                    position=position, price=None, availability=None, suspension=None,
                    effective_at=None, retrieved_at=timestamp(entry.get('retrieved_at')) or pos_row['imported_at'],
                    evidence_quality=entry.get('quality') or 'unclassified_retrospective_position',
                    source_payload_id=pos_evidence_id,
                    metadata={'state_kind': 'position_evidence', 'source_row_sha256': digest(entry),
                              'source_url': entry.get('source_url'),
                              'claimed_commit_date': entry.get('claimed_commit_date'),
                              'historical_deadline_proof': False}))
        for pid, positions in (pos_payload.get('conflicts') or {}).items():
            work.conflicts.append({'table': 'player_state', 'key': {'player_id': pid},
                                   'fields': ['position'], 'observed_positions': positions})

        # Source-specific fixture disagreements are retained, never promoted silently.
        official_obs = {row['fixture_id']: row for row in db.execute(select(m.fixture_observations).where(
            m.fixture_observations.c.source_payload_id == fixtures_evidence_id)).mappings()}
        local_obs = db.execute(select(m.fixture_observations).where(
            m.fixture_observations.c.source_payload_id == local_payload_id)).mappings()
        for row in local_obs:
            baseline = official_obs.get(row['fixture_id'])
            if baseline:
                fields = [field for field in ('gameweek_id', 'home_team_id', 'away_team_id',
                                               'status', 'home_score', 'away_score')
                          if row[field] != baseline[field]]
                if fields:
                    work.conflicts.append({'table': 'fixture_observations',
                                           'key': {'fixture_id': row['fixture_id']}, 'fields': fields})
        return {'status': 'complete' if not work.conflicts else 'complete_with_conflicts',
                'counts': {name: dict(counts) for name, counts in sorted(work.counts.items())},
                'conflicts': work.conflicts, 'unresolved': work.unresolved,
                'source_history_files': len(history_paths),
                'source_player_week_rows': sum(len(parsed(rows[0])) for rows in history_paths.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('import',))
    args = parser.parse_args()
    engine = engine_from_env()
    try:
        report = normalize(engine)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
