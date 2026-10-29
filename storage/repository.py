"""Read-only PostgreSQL comparison repository; not a runtime cutover switch."""
import json

from sqlalchemy import select

from storage.models import snapshots, predictions, evaluation_runs


class TrackingRepository:
    def __init__(self, engine):
        self.engine = engine

    def get_snapshot(self, snapshot_id):
        with self.engine.connect() as db:
            row = db.execute(select(snapshots).where(snapshots.c.id == snapshot_id)).mappings().first()
        if row is None:
            return None
        return {'id': row['id'], 'gameweek': row['gameweek'],
                'captured_at': row['captured_at_text'], 'deadline_at': row['deadline_at_text'],
                'deadline_source': row['deadline_source'], 'source': json.loads(row['source_text']),
                'classification': row['classification'], 'payload': json.loads(row['payload_text'])}

    def get_prediction(self, prediction_id):
        with self.engine.connect() as db:
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
        with self.engine.connect() as db:
            row = db.execute(select(evaluation_runs).where(evaluation_runs.c.id == run_id)).mappings().first()
        if row is None:
            return None
        return {'id': row['id'], 'snapshot_id': row['snapshot_id'], 'gameweek': row['gameweek'],
                'created_at': row['created_at_text'], 'source_digest': row['source_digest'],
                'status': row['status'], 'source': json.loads(row['source_text']),
                'payload': json.loads(row['payload_text'])}
