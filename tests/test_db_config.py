"""Local PostgreSQL configuration used by PyCharm and PowerShell startup."""
import pytest


def test_database_url_loads_from_project_env_when_process_env_absent(monkeypatch, tmp_path):
    from storage import db

    config = tmp_path / '.env'
    config.write_text('# local settings\nDATABASE_URL="postgresql+psycopg://u:p@127.0.0.1:5433/from_file"\n',
                      encoding='utf-8')
    monkeypatch.setattr(db, 'CONFIG_PATH', config)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    engine = db.engine_from_env()
    assert engine.url.database == 'from_file'
    engine.dispose()


def test_explicit_database_url_overrides_file_and_invalid_value_fails(monkeypatch, tmp_path):
    from storage import db

    config = tmp_path / '.env'
    config.write_text('DATABASE_URL=postgresql+psycopg://u:p@127.0.0.1:5433/from_file\n',
                      encoding='utf-8')
    monkeypatch.setattr(db, 'CONFIG_PATH', config)
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://u:p@127.0.0.1:5433/explicit')
    engine = db.engine_from_env()
    assert engine.url.database == 'explicit'
    engine.dispose()
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///unwanted.db')
    with pytest.raises(RuntimeError, match='PostgreSQL psycopg URL'):
        db.engine_from_env()
    assert not (tmp_path / 'unwanted.db').exists()
