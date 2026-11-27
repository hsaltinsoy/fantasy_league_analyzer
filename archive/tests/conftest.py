"""Keep legacy tests on their temporary SQLite paths after PostgreSQL cutover."""
import pytest


@pytest.fixture(autouse=True)
def explicit_test_storage_backend(monkeypatch, tmp_path):
    monkeypatch.setenv('STORAGE_BACKEND', 'sqlite')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    from storage import db
    monkeypatch.setattr(db, 'CONFIG_PATH', tmp_path / 'no-project-env')
