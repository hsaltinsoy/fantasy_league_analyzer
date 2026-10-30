"""Keep legacy tests on their temporary SQLite paths after PostgreSQL cutover."""
import pytest


@pytest.fixture(autouse=True)
def explicit_test_storage_backend(monkeypatch):
    monkeypatch.setenv('STORAGE_BACKEND', 'sqlite')
