from app import create_app
from storage.runtime_repository import OfficialDataUnavailable


def test_stale_fixtures_are_actionable_503_without_prediction_write(monkeypatch):
    monkeypatch.setenv('STORAGE_BACKEND', 'postgres')
    monkeypatch.setenv('DATABASE_URL',
        'postgresql+psycopg://invalid:invalid@127.0.0.1:1/isolated_test')
    monkeypatch.setattr('storage.runtime_repository.RuntimeRepository.fixture_archive',
                        lambda self, **kwargs: (_ for _ in ()).throw(
                            OfficialDataUnavailable('Current official fixtures are stale; run ingestion')))
    response = create_app().test_client().get(
        '/api/lineup/generate?week=11&model=short_form_3w&risk_profile=balanced&live=1&tow_weight=0')
    assert response.status_code == 503
    assert 'python -m storage.ingest_current' in response.get_json()['error']


def test_current_fixture_freshness_uses_retrieval_timestamp(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from storage.runtime_repository import RuntimeRepository
    import pytest
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, _):
            return self
        def first(self):
            return ({'data': {'gameweeks': []}}, old)
    class Engine:
        def connect(self): return Connection()
    with pytest.raises(OfficialDataUnavailable):
        RuntimeRepository(Engine()).fixture_archive(max_age_seconds=3600)
