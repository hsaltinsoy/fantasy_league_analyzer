"""Read-only PostgreSQL comparison repository; not a runtime cutover switch."""
import json
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from storage.models import snapshots, predictions, evaluation_runs
from storage.migrate_sqlite import _mapped

_capture_connection = ContextVar('tracking_capture_connection', default=None)


@contextmanager
def tracking_transaction(engine, *, join_existing=False):
    """Share one transaction across snapshot and prediction inserts."""
    if _capture_connection.get() is not None:
        if not join_existing:
            raise RuntimeError('Nested tracking transaction')
        yield
        return
    with engine.begin() as db:
        token = _capture_connection.set(db)
        try:
            yield
        finally:
            _capture_connection.reset(token)


@contextmanager
def _connection(engine, *, write=False):
    active = _capture_connection.get()
    if active is not None:
        yield active
    else:
        with (engine.begin() if write else engine.connect()) as db:
            yield db


class TrackingRepository:
    def __init__(self, engine):
        self.engine = engine

    def get_snapshot(self, snapshot_id):
        with _connection(self.engine) as db:
            row = db.execute(select(snapshots).where(snapshots.c.id == snapshot_id)).mappings().first()
        if row is None:
            return None
        return {'id': row['id'], 'gameweek': row['gameweek'],
                'captured_at': row['captured_at_text'], 'deadline_at': row['deadline_at_text'],
                'deadline_source': row['deadline_source'], 'source': json.loads(row['source_text']),
                'classification': row['classification'], 'payload': json.loads(row['payload_text'])}

    def get_prediction(self, prediction_id):
        with _connection(self.engine) as db:
            row = db.execute(select(predictions).where(predictions.c.id == prediction_id)).mappings().first()
        if row is None:
            return None
        return {'id': row['id'], 'snapshot_id': row['snapshot_id'], 'gameweek': row['gameweek'],
                'created_at': row['created_at_text'], 'status': row['status'], 'model': row['model'],
                'model_version': row['model_version'], 'risk_strategy': row['risk_strategy'],
                'raw_expected_points': float(row['raw_expected_points']),
                'risk_adjusted_objective': (float(row['risk_adjusted_objective'])
                                            if row['risk_adjusted_objective'] is not None else None),
                'payload': json.loads(row['payload_text'])}

    def get_evaluation_run(self, run_id):
        with _connection(self.engine) as db:
            row = db.execute(select(evaluation_runs).where(evaluation_runs.c.id == run_id)).mappings().first()
        if row is None:
            return None
        return {'id': row['id'], 'snapshot_id': row['snapshot_id'], 'gameweek': row['gameweek'],
                'created_at': row['created_at_text'], 'source_digest': row['source_digest'],
                'status': row['status'], 'source': json.loads(row['source_text']),
                'payload': json.loads(row['payload_text'])}

    def save_snapshot(self, row):
        """Insert one immutable SQLite-shaped snapshot; same ID and bytes are idempotent."""
        mapped = _mapped('snapshots', row)
        with _connection(self.engine, write=True) as db:
            existing = db.execute(select(snapshots.c.source_sha256).where(snapshots.c.id == row['id'])).scalar_one_or_none()
            if existing is not None and existing != mapped['source_sha256']:
                raise ValueError('Conflicting immutable snapshot ID')
            db.execute(insert(snapshots).values(**mapped).on_conflict_do_nothing(index_elements=['id']))
        return self.get_snapshot(row['id'])

    def save_predictions(self, rows):
        """Insert a complete prediction batch atomically; reject conflicting IDs."""
        if not rows:
            raise ValueError('At least one prediction required')
        saved_ids = []
        with _connection(self.engine, write=True) as db:
            for row in rows:
                db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'),
                           {'key': row['snapshot_id']})
                mapped = _mapped('predictions', row)
                snapshot = db.execute(select(snapshots.c.gameweek).where(
                    snapshots.c.id == row['snapshot_id']).with_for_update()).scalar_one_or_none()
                if snapshot != row['gameweek']:
                    raise ValueError('Unknown snapshot or prediction gameweek mismatch')
                duplicate = db.execute(select(predictions.c.id).where(
                    predictions.c.snapshot_id == row['snapshot_id'],
                    predictions.c.model == row['model'],
                    predictions.c.model_version == row['model_version'],
                    predictions.c.risk_strategy == row['risk_strategy'],
                    predictions.c.payload_text == row['payload'])).scalar_one_or_none()
                if duplicate:
                    saved_ids.append(duplicate)
                    continue
                existing = db.execute(select(predictions.c.source_sha256).where(
                    predictions.c.id == row['id'])).scalar_one_or_none()
                if existing is not None and existing != mapped['source_sha256']:
                    raise ValueError('Conflicting immutable prediction ID')
                db.execute(insert(predictions).values(**mapped).on_conflict_do_nothing(index_elements=['id']))
                saved_ids.append(row['id'])
        return [self.get_prediction(row_id) for row_id in saved_ids]

    def save_evaluation_run(self, row):
        mapped = _mapped('evaluation_runs', row)
        with _connection(self.engine, write=True) as db:
            week = db.execute(select(snapshots.c.gameweek).where(
                snapshots.c.id == row['snapshot_id']).with_for_update()).scalar_one_or_none()
            if week != row['gameweek']:
                raise ValueError('Evaluation snapshot/gameweek mismatch')
            existing = db.execute(select(evaluation_runs).where(
                evaluation_runs.c.snapshot_id == row['snapshot_id'],
                evaluation_runs.c.source_digest == row['source_digest'])).mappings().first()
            if existing:
                if existing['payload_text'] != row['payload'] or existing['source_text'] != row['source']:
                    raise ValueError('Conflicting evaluation for source digest')
                return self.get_evaluation_run(existing['id'])
            db.execute(insert(evaluation_runs).values(**mapped))
        return self.get_evaluation_run(row['id'])

    def prediction_ids(self, snapshot_id=None):
        query = select(predictions.c.id).order_by(predictions.c.created_at, predictions.c.id)
        if snapshot_id is not None:
            query = query.where(predictions.c.snapshot_id == snapshot_id)
        with _connection(self.engine) as db:
            return list(db.execute(query).scalars())

    def latest_evaluation_run(self, snapshot_id):
        query = select(evaluation_runs.c.id).where(evaluation_runs.c.snapshot_id == snapshot_id).order_by(
            evaluation_runs.c.created_at.desc(), evaluation_runs.c.id.desc()).limit(1)
        with _connection(self.engine) as db:
            run_id = db.execute(query).scalar_one_or_none()
        return self.get_evaluation_run(run_id) if run_id else None
