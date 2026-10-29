"""SQLAlchemy connection factory; no implicit file-store fallback."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def engine_from_env():
    url = os.environ.get('DATABASE_URL')
    if not url or not url.startswith('postgresql+psycopg://'):
        raise RuntimeError('Set DATABASE_URL to a PostgreSQL psycopg URL')
    return create_engine(url, pool_pre_ping=True)


def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
