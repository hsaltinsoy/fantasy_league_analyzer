from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from storage.models import metadata

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = metadata


def run_migrations_offline():
    raise RuntimeError('Offline migrations are disabled; use a live PostgreSQL connection')


def run_migrations_online():
    from storage.db import engine_from_env
    engine = engine_from_env()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True, transactional_ddl=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
