"""Run against an isolated DB by setting PHASE17_TEST_DATABASE_URL."""
import os
import shutil
import sqlite3

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import DBAPIError

from storage.db import engine_from_env
from storage.migrate_sqlite import import_tracking, reconcile
from storage.models import snapshots, predictions, source_artifacts
from storage.repository import TrackingRepository
from storage.import_artifacts import import_artifacts, reconcile_artifacts
from analysis.prediction_tracking import get_snapshot, get_prediction

SOURCE = 'historical_data/prediction_tracking.sqlite3'
ORIGINAL = '1e9f5094-9b24-42f6-a0ff-ddf201685aa8'


@pytest.fixture(scope='module')
def engine():
    url = os.getenv('PHASE17_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set PHASE17_TEST_DATABASE_URL for isolated PostgreSQL integration tests')
    if not url.endswith('/fantasy_league_phase17_test'):
        pytest.fail('Integration tests require the dedicated fantasy_league_phase17_test DB')
    db = create_engine(url, pool_pre_ping=True)
    import_tracking(SOURCE, db)
    yield db
    db.dispose()


def test_connection_schema_and_repeatable_import(engine):
    second = import_tracking(SOURCE, engine)
    assert second['snapshots']['source'] == 9
    assert second['snapshots']['inserted'] == 0
    assert second['predictions']['already_identical'] == 19
    assert reconcile(SOURCE, engine)['status'] == 'passed'


def test_gw10_content_and_repository_parity(engine):
    repo = TrackingRepository(engine)
    assert repo.get_snapshot(ORIGINAL) == get_snapshot(ORIGINAL)
    with engine.connect() as db:
        ids = db.execute(select(predictions.c.id).where(predictions.c.snapshot_id == ORIGINAL)).scalars().all()
    assert len(ids) == 11
    for prediction_id in ids:
        migrated = repo.get_prediction(prediction_id)
        source = get_prediction(prediction_id)
        assert migrated.pop('raw_expected_points') == pytest.approx(source.pop('raw_expected_points'), abs=0.000001)
        risk = migrated.pop('risk_adjusted_objective')
        source_risk = source.pop('risk_adjusted_objective')
        if risk is None:
            assert source_risk is None
        else:
            assert risk == pytest.approx(source_risk, abs=0.000001)
        assert migrated == source


def test_immutability_and_transaction_rollback(engine, tmp_path):
    with pytest.raises(DBAPIError):
        with engine.begin() as db:
            db.execute(snapshots.update().where(snapshots.c.id == ORIGINAL).values(classification='changed'))
    changed = tmp_path / 'conflict.sqlite3'
    shutil.copyfile(SOURCE, changed)
    with sqlite3.connect(changed) as db:
        db.execute('DROP TRIGGER snapshots_no_update')
        db.execute("INSERT INTO snapshots SELECT '00000000-phase17-test', gameweek, captured_at, deadline_at, deadline_source, source, classification, payload FROM snapshots LIMIT 1")
        db.execute("UPDATE snapshots SET classification='tampered' WHERE id=?", (ORIGINAL,))
    with pytest.raises(ValueError, match='Conflicting snapshots ID'):
        import_tracking(changed, engine)
    with engine.connect() as db:
        assert db.execute(select(snapshots.c.id).where(snapshots.c.id == '00000000-phase17-test')).scalar_one_or_none() is None
    assert reconcile(SOURCE, engine)['status'] == 'passed'


def test_missing_postgres_configuration_never_falls_back(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        engine_from_env()


def test_artifact_import_exact_bytes_and_immutability(engine, tmp_path):
    folder = tmp_path / 'historical_data'
    folder.mkdir()
    sample = folder / 'phase17_test_evidence.json'
    sample.write_text('{"classification":"retrospective","rows":[1,2]}', encoding='utf-8')
    first = import_artifacts(tmp_path, engine)
    second = import_artifacts(tmp_path, engine)
    assert first['source_files'] == 1
    assert second['inserted_versions'] == 0
    assert reconcile_artifacts(tmp_path, engine)['exact_matches'] == 1
    with engine.connect() as db:
        row = db.execute(select(source_artifacts).where(
            source_artifacts.c.source_path == 'historical_data/phase17_test_evidence.json')).mappings().first()
    assert row['raw_bytes'] == sample.read_bytes()
    with pytest.raises(DBAPIError):
        with engine.begin() as db:
            db.execute(source_artifacts.update().where(
                source_artifacts.c.source_path == row['source_path'],
                source_artifacts.c.content_sha256 == row['content_sha256']).values(category='changed'))
