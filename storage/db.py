"""SQLAlchemy connection factory; no implicit file-store fallback."""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

CONFIG_PATH = Path(__file__).resolve().parents[1] / '.env'


def _database_url_from_config(path=None):
    """Read the local connection setting without putting credentials in logs."""
    path = path or CONFIG_PATH
    if not path.is_file():
        return None
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        key, separator, value = line.partition('=')
        if separator and key.strip() == 'DATABASE_URL':
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            return value
    return None


def engine_from_env():
    url = (os.environ['DATABASE_URL'] if 'DATABASE_URL' in os.environ
           else _database_url_from_config())
    if not url or not url.startswith('postgresql+psycopg://'):
        raise RuntimeError('Set DATABASE_URL to a PostgreSQL psycopg URL')
    return create_engine(url, pool_pre_ping=True)


def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
