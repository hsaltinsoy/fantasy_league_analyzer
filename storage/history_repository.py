"""Read-only, chronological PostgreSQL access to normalized football history."""
from decimal import Decimal

from sqlalchemy import select

from storage import models as m


class HistoricalRepository:
    def __init__(self, engine):
        self.engine = engine

    def fixtures_by_gameweek(self, week, *, as_of=None):
        query = (select(m.fixtures, m.source_payloads.c.retrieved_at.label('source_retrieved_at'),
                        m.source_payloads.c.evidence_quality)
                 .join(m.source_payloads, m.fixtures.c.source_payload_id == m.source_payloads.c.id)
                 .where(m.fixtures.c.gameweek_id == week))
        if as_of is not None:
            query = query.where(m.source_payloads.c.retrieved_at.is_not(None),
                                m.source_payloads.c.retrieved_at <= as_of)
        with self.engine.connect() as db:
            return [dict(row) for row in db.execute(query.order_by(m.fixtures.c.kickoff_at,
                                                                    m.fixtures.c.id)).mappings()]

    def historical_player_statistics(self, player_id, *, before_week, as_of=None, appearances_only=False):
        if before_week < 1:
            raise ValueError('before_week must be positive')
        query = (select(m.player_gameweek_stats, m.source_payloads.c.retrieved_at.label('source_retrieved_at'),
                        m.source_payloads.c.evidence_quality)
                 .join(m.source_payloads, m.player_gameweek_stats.c.source_payload_id == m.source_payloads.c.id)
                 .where(m.player_gameweek_stats.c.player_id == str(player_id),
                        m.player_gameweek_stats.c.gameweek_id < before_week))
        if appearances_only:
            query = query.where(m.player_gameweek_stats.c.minutes > 0)
        if as_of is not None:
            query = query.where(m.source_payloads.c.retrieved_at.is_not(None),
                                m.source_payloads.c.retrieved_at <= as_of)
        with self.engine.connect() as db:
            return [dict(row) for row in db.execute(query.order_by(
                m.player_gameweek_stats.c.gameweek_id,
                m.player_gameweek_stats.c.fixture_id)).mappings()]

    def player_form(self, player_id, *, target_week, previous_weeks, as_of=None,
                    appearances_only=False):
        if target_week < 1 or previous_weeks < 1:
            raise ValueError('target_week and previous_weeks must be positive')
        rows = self.historical_player_statistics(player_id, before_week=target_week,
                                                 as_of=as_of, appearances_only=appearances_only)
        usable = [row for row in rows if row['gameweek_id'] >= target_week - previous_weeks
                  and row['fantasy_points'] is not None]
        mean = sum((row['fantasy_points'] for row in usable), Decimal(0)) / len(usable) if usable else None
        return {'player_id': str(player_id), 'target_week': target_week,
                'window_weeks': previous_weeks, 'observations': len(usable),
                'mean_points': mean, 'conditional_on_appearance': appearances_only,
                'evidence_cutoff': as_of}

    def historical_states(self, player_id, *, before_week, as_of=None):
        if before_week < 1:
            raise ValueError('before_week must be positive')
        query = select(m.player_state).where(
            m.player_state.c.player_id == str(player_id),
            m.player_state.c.effective_gameweek.is_not(None),
            m.player_state.c.effective_gameweek < before_week)
        if as_of is not None:
            query = query.where(m.player_state.c.retrieved_at <= as_of,
                m.player_state.c.metadata['historical_deadline_proof'].as_boolean().is_(True))
        with self.engine.connect() as db:
            return [dict(row) for row in db.execute(query.order_by(
                m.player_state.c.effective_gameweek, m.player_state.c.id)).mappings()]

    def positions_and_clubs(self, player_id, *, before_week, as_of=None):
        """Return all evidence, including disagreements; never choose by name."""
        rows = self.historical_states(player_id, before_week=before_week, as_of=as_of)
        return [{'effective_gameweek': row['effective_gameweek'],
                 'position': row['position'], 'team_id': row['team_id'],
                 'evidence_quality': row['evidence_quality'],
                 'source_payload_id': row['source_payload_id'],
                 'retrieved_at': row['retrieved_at']}
                for row in rows if row['position'] is not None or row['team_id'] is not None]

    def players_by_gameweek(self, week, *, as_of=None):
        if week < 1:
            raise ValueError('week must be positive')
        query = select(m.players.c.id, m.players.c.name).order_by(m.players.c.id)
        with self.engine.connect() as db:
            people = [dict(row) for row in db.execute(query).mappings()]
            state_query = select(m.player_state).where(
                m.player_state.c.effective_gameweek.is_not(None),
                m.player_state.c.effective_gameweek <= week)
            if as_of is not None:
                state_query = state_query.where(m.player_state.c.retrieved_at <= as_of,
                    m.player_state.c.metadata['historical_deadline_proof'].as_boolean().is_(True))
            state_rows = [dict(row) for row in db.execute(state_query).mappings()]
        grouped = {}
        for state in state_rows:
            grouped.setdefault(state['player_id'], []).append(state)
        for person in people:
            states = grouped.get(person['id'], [])
            # Never silently choose among conflicting historical evidence.
            person['position_evidence'] = [row for row in states if row['position'] is not None]
            person['club_evidence'] = [row for row in states if row['team_id'] is not None]
            person['price_evidence'] = [row for row in states if row['price'] is not None]
            person['availability_evidence'] = [row for row in states if row['availability'] is not None]
        return people

    def resolve_identity(self, provider, provider_player_id):
        if not provider or provider_player_id is None:
            return None
        query = select(m.player_identity_mappings).where(
            m.player_identity_mappings.c.provider == provider,
            m.player_identity_mappings.c.provider_player_id == str(provider_player_id))
        with self.engine.connect() as db:
            rows = [dict(row) for row in db.execute(query).mappings()]
        if len(rows) > 1:
            raise ValueError('Ambiguous provider identity; no automatic merge')
        return rows[0] if rows else None

    def provenance(self, source_payload_id):
        query = (select(m.source_payloads, m.collection_runs.c.source_id,
                        m.collection_runs.c.metadata.label('run_metadata'))
                 .join(m.collection_runs, m.source_payloads.c.run_id == m.collection_runs.c.id)
                 .where(m.source_payloads.c.id == source_payload_id))
        with self.engine.connect() as db:
            row = db.execute(query).mappings().first()
        return dict(row) if row else None
