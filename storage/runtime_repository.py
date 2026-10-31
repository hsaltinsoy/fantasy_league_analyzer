"""PostgreSQL runtime reads and transactional current-state ingestion."""
import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from storage import models as m
from storage.history_repository import HistoricalRepository
from analysis.prediction_tracking import parse_time


class OfficialDataUnavailable(RuntimeError):
    """Required current official API evidence is absent or past its freshness limit."""


def _upsert(db, table, values, keys):
    statement = insert(table).values(**values)
    db.execute(statement.on_conflict_do_update(index_elements=keys, set_={
        key: statement.excluded[key] for key in values if key not in keys}))


class RuntimeRepository(HistoricalRepository):
    def save_generated_report(self, report_type, content):
        """Store an immutable generated report; identical content is idempotent."""
        if not isinstance(report_type, str) or not report_type or not isinstance(content, dict):
            raise ValueError('Report type and object content required')
        raw = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                         allow_nan=False)
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        source_path = 'runtime/' + report_type
        with self.engine.begin() as db:
            existing = db.execute(select(m.historical_reports.c.id).where(
                m.historical_reports.c.source_path == source_path,
                m.historical_reports.c.content_sha256 == digest)).scalar_one_or_none()
            if existing is not None:
                return existing
            report_id = str(uuid.uuid4())
            db.execute(insert(m.historical_reports).values(
                id=report_id, report_type=report_type, source_path=source_path,
                content_sha256=digest, content=content,
                evidence_quality='generated_from_postgres_runtime',
                imported_at=datetime.now(timezone.utc)).on_conflict_do_nothing(
                    index_elements=['source_path', 'content_sha256']))
            return db.execute(select(m.historical_reports.c.id).where(
                m.historical_reports.c.source_path == source_path,
                m.historical_reports.c.content_sha256 == digest)).scalar_one()

    def latest_generated_report(self, report_type):
        if not isinstance(report_type, str) or not report_type:
            raise ValueError('Report type required')
        with self.engine.connect() as db:
            row = db.execute(select(m.historical_reports).where(
                m.historical_reports.c.source_path == 'runtime/' + report_type).order_by(
                m.historical_reports.c.imported_at.desc(),
                m.historical_reports.c.id.desc()).limit(1)).mappings().first()
        return dict(row) if row else None

    def artifact_json(self, source_path, *, sha256=None):
        query = select(m.source_artifacts.c.raw_bytes, m.source_artifacts.c.content_sha256).where(
            m.source_artifacts.c.source_path == source_path)
        if sha256 is not None:
            query = query.where(m.source_artifacts.c.content_sha256 == sha256)
        with self.engine.connect() as db:
            rows = db.execute(query).all()
        if len(rows) != 1:
            raise ValueError(f'Expected one staged artifact: {source_path}; found {len(rows)}')
        raw, digest = rows[0]
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f'Artifact digest mismatch: {source_path}')
        return json.loads(raw.decode('utf-8-sig'))

    def phase15_training_inputs(self, target_week):
        recovery = self.artifact_json('historical_data/recovered/coverage_report.json')
        manifest = self.artifact_json('historical_data/recovered/official_collection_manifest.json')
        position_entry = recovery['position_evidence']
        positions = self.artifact_json('historical_data/recovered/' + position_entry['path'],
                                       sha256=position_entry['sha256'])
        fixture_entry = manifest['entries']['fixtures_current']
        raw = self.artifact_json('historical_data/recovered/' + fixture_entry['relative_path'],
                                 sha256=fixture_entry['sha256'])
        fixtures = {int(item['order']): {'gameweek_id': item['id'], 'matches': item['matches']}
            for item in raw['data']['gameweeks'] if isinstance(item, dict)
            and isinstance(item.get('order'), int)}
        # The most recent allowed training label is target_week - 2.
        records = self.historical_records(before_week=target_week - 1)
        with self.engine.connect() as db:
            coverage_digest = db.execute(select(m.source_artifacts.c.content_sha256).where(
                m.source_artifacts.c.source_path == 'historical_data/recovered/coverage_report.json')).scalar_one()
        return recovery, positions, fixtures, records, coverage_digest

    def team_of_week(self):
        from analysis.team_of_week_v36 import parse
        payload = self.historical_report('historical_data/team_of_week_verified.json')
        if payload is None:
            raise RuntimeError('Team-of-week evidence is unavailable in PostgreSQL')
        return parse(payload)

    def historical_report(self, source_path):
        query = select(m.source_artifacts.c.raw_bytes).where(
            m.source_artifacts.c.source_path == source_path)
        with self.engine.connect() as db:
            rows = db.execute(query).scalars().all()
        if len(rows) > 1:
            raise ValueError(f'Multiple report versions for {source_path}; select evidence explicitly')
        return json.loads(rows[0].decode('utf-8-sig')) if rows else None

    def verified_identity_crosswalk(self):
        query = select(m.player_identity_mappings).where(
            m.player_identity_mappings.c.provider == 'xgedge',
            m.player_identity_mappings.c.confidence == 'verified',
            m.player_identity_mappings.c.valid_to.is_(None)).order_by(
            m.player_identity_mappings.c.player_id)
        with self.engine.connect() as db:
            rows = db.execute(query).mappings().all()
        return {'version': 1, 'entries': [
            {'tff_id': int(row['player_id']), 'profile_url': row['provider_player_id'],
             'aliases': [row['name_alias']] if row['name_alias'] else [], 'verified': True,
             'evidence': row['evidence_id']}
            for row in rows if row['provider_player_id']]}

    def add_verified_identity(self, tff_id, profile_url, evidence, *, aliases=()):
        """Append a reviewed external identity and keep its exact review evidence."""
        player_id = str(tff_id)
        if not player_id.isdigit() or not profile_url.startswith('https://www.xg-edge.com/players/') or not evidence:
            raise ValueError('TFF ID, xgEdge profile URL and evidence are required')
        now = datetime.now(timezone.utc)
        raw = {'tff_id': player_id, 'profile_url': profile_url,
               'evidence': evidence, 'aliases': list(aliases), 'reviewed_at': now.isoformat()}
        raw_text = json.dumps(raw, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()
        evidence_id = 'manual-identity:' + digest
        mapping_id = 'verified-xgedge:' + digest
        with self.engine.begin() as db:
            db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('verified-xgedge-identity', 0))"))
            if db.execute(select(m.players.c.id).where(m.players.c.id == player_id)).scalar_one_or_none() is None:
                raise ValueError(f'Unknown official TFF player ID: {player_id}')
            active = db.execute(select(m.player_identity_mappings).where(
                m.player_identity_mappings.c.provider == 'xgedge',
                m.player_identity_mappings.c.confidence == 'verified',
                m.player_identity_mappings.c.valid_to.is_(None))).mappings().all()
            if any(row['provider_player_id'] == profile_url and row['player_id'] != player_id for row in active):
                raise ValueError('Profile URL is linked to another TFF player')
            if any(row['provider_player_id'] == profile_url and row['player_id'] == player_id for row in active):
                raise ValueError('Identity link already exists')
            db.execute(insert(m.data_sources).values(id='manual-identity-review',
                name='Manual identity review', kind='manual_review', url=None, metadata={})
                .on_conflict_do_nothing(index_elements=['id']))
            db.execute(insert(m.collection_runs).values(id=evidence_id,
                source_id='manual-identity-review', retrieved_at=now, status='complete',
                content_hash=digest, error=None, metadata={'player_id': player_id})
                .on_conflict_do_nothing(index_elements=['id']))
            db.execute(insert(m.source_payloads).values(id=evidence_id,
                run_id=evidence_id, source_path='manual_identity_review',
                content_sha256=digest, raw_payload=raw, raw_text=raw_text,
                retrieved_at=now, evidence_quality='manually_verified_identity')
                .on_conflict_do_nothing(index_elements=['id']))
            db.execute(m.player_identity_mappings.update().where(
                m.player_identity_mappings.c.player_id == player_id,
                m.player_identity_mappings.c.provider == 'xgedge',
                m.player_identity_mappings.c.confidence == 'verified',
                m.player_identity_mappings.c.valid_to.is_(None)).values(valid_to=now))
            db.execute(insert(m.player_identity_mappings).values(id=mapping_id,
                player_id=player_id, provider='xgedge', provider_player_id=profile_url,
                name_alias=str(aliases[0]) if aliases else None, confidence='verified',
                version=now.isoformat(), valid_from=now, valid_to=None,
                evidence_id=evidence_id))
        from data_sources.identity import crosswalk_version
        return crosswalk_version(self.verified_identity_crosswalk())

    def latest_lineup(self, week, *, model_version='v3.9'):
        query = select(m.predictions.c.id).where(
            m.predictions.c.gameweek == week,
            m.predictions.c.model_version == model_version).order_by(
            m.predictions.c.created_at.desc(), m.predictions.c.id.desc()).limit(1)
        with self.engine.connect() as db:
            prediction_id = db.execute(query).scalar_one_or_none()
        if prediction_id is None:
            return None
        from storage.repository import TrackingRepository
        item = TrackingRepository(self.engine).get_prediction(prediction_id)
        return {**item['payload'], 'prediction_tracking': {
            'id': item['id'], 'snapshot_id': item['snapshot_id'],
            'created_at': item['created_at'], 'status': item['status']}}

    def current_player_pool(self, *, max_age_seconds=None):
        """Return the exact official projection rows from the latest persisted API response."""
        from data_sources.tff_official import _extract
        query = select(m.source_payloads.c.raw_payload, m.source_payloads.c.retrieved_at).where(
            m.source_payloads.c.evidence_quality == 'current_official_api',
            m.source_payloads.c.id.like('tff-current-%')).order_by(
            m.source_payloads.c.retrieved_at.desc(), m.source_payloads.c.id.desc()).limit(1)
        with self.engine.connect() as db:
            row = db.execute(query).first()
        if row is None:
            raise OfficialDataUnavailable('No current official player pool in PostgreSQL; run ingestion')
        raw, retrieved = row
        if max_age_seconds is not None and (retrieved is None or
            (datetime.now(timezone.utc) - retrieved).total_seconds() > max_age_seconds):
            raise OfficialDataUnavailable('Current official player pool is stale; run ingestion')
        return _extract(raw)

    def historical_records(self, *, before_week, as_of=None):
        """Exact archived rows with a mandatory gameweek and optional evidence-time cutoff."""
        if before_week < 1:
            raise ValueError('before_week must be positive')
        query = select(m.source_payloads.c.source_path, m.source_payloads.c.raw_payload,
            m.source_payloads.c.retrieved_at).where(
            m.source_payloads.c.source_path.like('historical_data/player_%.json'))
        if as_of is not None:
            query = query.where(m.source_payloads.c.retrieved_at.is_not(None),
                                m.source_payloads.c.retrieved_at <= as_of)
        with self.engine.connect() as db:
            rows = db.execute(query).all()
        histories = {}
        for path, payload, retrieved_at in rows:
            pid = path.removeprefix('historical_data/player_').removesuffix('.json')
            if not pid.isdigit() or not isinstance(payload, list):
                continue
            if pid in histories:
                raise ValueError(f'Multiple history versions for player {pid}')
            histories[pid] = [item for item in payload if isinstance(item, dict)
                and str(item.get('gameweekOrder', '')).isdigit()
                and int(item['gameweekOrder']) < before_week]
        return histories

    def fixture_archive(self, *, max_age_seconds=None):
        query = select(m.source_payloads.c.raw_payload, m.source_payloads.c.retrieved_at).where(
            m.source_payloads.c.id.like('tff-fixtures-%')).order_by(
            m.source_payloads.c.retrieved_at.desc(), m.source_payloads.c.id.desc()).limit(1)
        with self.engine.connect() as db:
            row = db.execute(query).first()
        if row is None:
            raise OfficialDataUnavailable('No current official fixtures in PostgreSQL; run ingestion')
        raw, retrieved = row
        if max_age_seconds is not None and (retrieved is None or
            (datetime.now(timezone.utc) - retrieved).total_seconds() > max_age_seconds):
            raise OfficialDataUnavailable('Current official fixtures are stale; run ingestion')
        weeks = (raw.get('data') or {}).get('gameweeks') if isinstance(raw, dict) else None
        if not isinstance(weeks, list):
            raise ValueError('Persisted official fixture payload is invalid')
        result = {}
        for week in weeks:
            result[str(week['order'])] = {'gameweek_id': week.get('id'),
                'deadline': week.get('deadline'), 'matches': [
                    {key: match.get(key) for key in ('id', 'homeClubId', 'awayClubId',
                        'kickoffAt', 'homeScore', 'awayScore', 'status')}
                    for match in week['matches']]}
        from analysis.live_benchmark import FIXTURE_ENDPOINT
        from data_sources.tff_official import BASE
        return {'weeks': result, 'captured_utc': retrieved.isoformat(),
                'source_endpoint': FIXTURE_ENDPOINT, 'source_url': BASE + FIXTURE_ENDPOINT}

    def teams(self):
        with self.engine.connect() as db:
            return [dict(row) for row in db.execute(select(m.teams).order_by(m.teams.c.id)).mappings()]

    def gameweeks(self):
        with self.engine.connect() as db:
            return [dict(row) for row in db.execute(select(m.gameweeks).order_by(m.gameweeks.c.id)).mappings()]

    def current_players(self):
        with self.engine.connect() as db:
            people = db.execute(select(m.players)).mappings().all()
            states = db.execute(select(m.player_state).where(
                m.player_state.c.evidence_quality == 'current_official_api').order_by(
                m.player_state.c.retrieved_at.desc(), m.player_state.c.id.desc())).mappings().all()
        latest = {}
        for state in states:
            latest.setdefault(state['player_id'], dict(state))
        return [{**dict(person), 'state': latest[person['id']]} for person in people if person['id'] in latest]

    def ingest_current_players(self, feed):
        """Persist exact API evidence and a separate, nonhistorical state observation."""
        raw = feed.get('raw_payload')
        retrieved = feed.get('retrieved_at')
        if raw is None or not isinstance(retrieved, datetime) or retrieved.tzinfo is None:
            raise ValueError('Raw payload and timezone-aware retrieval timestamp required')
        rows = feed['players']
        if not rows:
            raise ValueError('Empty player pool')
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        run_id = 'tff-current-' + hashlib.sha256((digest + retrieved.isoformat()).encode()).hexdigest()
        source_id = 'tff-current-api'
        inserted = skipped = unresolved = conflicting = 0
        with self.engine.begin() as db:
            _upsert(db, m.data_sources, {'id': source_id, 'name': 'TFF current API',
                'url': feed.get('source_url'), 'kind': 'official_api', 'metadata': {}}, ['id'])
            db.execute(insert(m.collection_runs).values(id=run_id, source_id=source_id,
                retrieved_at=retrieved, status='complete', content_hash=digest,
                error=None, metadata={'count': len(rows)})
                .on_conflict_do_nothing(index_elements=['id']))
            db.execute(insert(m.source_payloads).values(id=run_id, run_id=run_id,
                source_path=feed.get('source_url'), content_sha256=digest,
                raw_payload=raw, raw_text=json.dumps(raw, ensure_ascii=False),
                retrieved_at=retrieved, evidence_quality='current_official_api')
                .on_conflict_do_nothing(index_elements=['id']))
            for row in rows:
                pid = str(row['id'])
                team_id = str(row['club_id']) if row.get('club_id') is not None else None
                if row.get('price') is None or row.get('position') is None or team_id is None:
                    unresolved += 1
                if team_id:
                    db.execute(insert(m.teams).values(id=team_id, name=team_id,
                        source_id=source_id, metadata={'name_unverified': True})
                        .on_conflict_do_nothing(index_elements=['id']))
                db.execute(insert(m.players).values(id=pid, name=row['name'],
                    source_id=source_id, metadata={}).on_conflict_do_nothing(index_elements=['id']))
                db.execute(insert(m.player_identity_mappings).values(id=f'tff:{pid}', player_id=pid,
                    provider='tff', provider_player_id=pid, name_alias=row['name'],
                    confidence='exact_provider_id', version='current',
                    valid_from=None, valid_to=None, evidence_id=run_id)
                    .on_conflict_do_nothing(index_elements=['id']))
                state_id = f'current:{run_id}:{pid}'
                prior = db.execute(select(m.player_state.c.id).where(m.player_state.c.id == state_id)).scalar_one_or_none()
                inserted += prior is None
                skipped += prior is not None
                db.execute(insert(m.player_state).values(id=state_id, player_id=pid,
                    gameweek_id=None, effective_gameweek=None, team_id=team_id,
                    position=row.get('position'), price=row.get('price'),
                    availability=row.get('availability'), suspension=None, effective_at=None,
                    retrieved_at=retrieved, evidence_quality='current_official_api',
                    source_payload_id=run_id, metadata={'availability_percent': row.get('availability_percent')})
                    .on_conflict_do_nothing(index_elements=['id']))
        return {'source_payload_id': run_id, 'players': len(rows), 'retrieved_at': retrieved,
                'inserted': inserted, 'skipped': skipped, 'unresolved': unresolved,
                'conflicting': conflicting}

    def ingest_current_fixtures(self, feed):
        raw = feed.get('raw_payload')
        retrieved = parse_time(feed.get('captured_utc'))
        if raw is None or retrieved is None or not isinstance(feed.get('weeks'), dict):
            raise ValueError('Raw fixture evidence and retrieval timestamp required')
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        run_id = 'tff-fixtures-' + hashlib.sha256((digest + retrieved.isoformat()).encode()).hexdigest()
        source_id = 'tff-fixtures-api'
        inserted = skipped = unresolved = conflicting = 0
        with self.engine.begin() as db:
            _upsert(db, m.data_sources, {'id': source_id, 'name': 'TFF fixtures API',
                'url': feed.get('source_url'), 'kind': 'official_api', 'metadata': {}}, ['id'])
            db.execute(insert(m.collection_runs).values(id=run_id, source_id=source_id,
                retrieved_at=retrieved, status='complete', content_hash=digest, error=None,
                metadata={}).on_conflict_do_nothing(index_elements=['id']))
            db.execute(insert(m.source_payloads).values(id=run_id, run_id=run_id,
                source_path=feed.get('source_url'), content_sha256=digest, raw_payload=raw,
                raw_text=json.dumps(raw, ensure_ascii=False), retrieved_at=retrieved,
                evidence_quality='current_official_api').on_conflict_do_nothing(index_elements=['id']))
            for week_text, entry in feed['weeks'].items():
                week = int(week_text)
                db.execute(insert(m.gameweeks).values(id=week, official_id=str(entry.get('gameweek_id')),
                    deadline_at=parse_time(entry.get('deadline')), deadline_source_id=source_id,
                    deadline_retrieved_at=retrieved, metadata={})
                    .on_conflict_do_nothing(index_elements=['id']))
                for match in entry['matches']:
                    fid = match.get('id')
                    home, away = match.get('homeClubId'), match.get('awayClubId')
                    if fid is None or home is None or away is None or home == away:
                        unresolved += 1
                        continue
                    fid, home, away = str(fid), str(home), str(away)
                    for team_id in (home, away):
                        db.execute(insert(m.teams).values(id=team_id, name=team_id,
                            source_id=source_id, metadata={'name_unverified': True})
                            .on_conflict_do_nothing(index_elements=['id']))
                    existing = db.execute(select(m.fixtures).where(m.fixtures.c.id == fid)).mappings().first()
                    if existing:
                        skipped += 1
                        if (existing['gameweek_id'], existing['home_team_id'], existing['away_team_id']) != (week, home, away):
                            conflicting += 1
                    else:
                        db.execute(insert(m.fixtures).values(id=fid, gameweek_id=week,
                            home_team_id=home, away_team_id=away,
                            kickoff_at=parse_time(match.get('kickoffAt')),
                            status=match.get('status'), source_payload_id=run_id))
                        inserted += 1
                    observation_id = f'{run_id}:{fid}'
                    db.execute(insert(m.fixture_observations).values(id=observation_id,
                        fixture_id=fid, source_payload_id=run_id, gameweek_id=week,
                        home_team_id=home, away_team_id=away, status=match.get('status'),
                        home_score=match.get('homeScore'), away_score=match.get('awayScore'),
                        source_quality='current_official_api', metadata={})
                        .on_conflict_do_nothing(index_elements=['id']))
        return {'source_payload_id': run_id, 'inserted': inserted, 'skipped': skipped,
                'unresolved': unresolved, 'conflicting': conflicting}
