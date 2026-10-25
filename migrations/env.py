"""Alembic environment for harness-owned PostgreSQL tables."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.conf.settings import get_settings
from app.harness.database import sqlalchemy_postgres_dsn
from app.harness.db_models import HarnessBase

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = HarnessBase.metadata


def run_migrations_offline() -> None:
    settings = get_settings()
    context.configure(
        url=sqlalchemy_postgres_dsn(settings.postgres_dsn),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = get_settings()
    engine = create_engine(
        sqlalchemy_postgres_dsn(settings.postgres_dsn),
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
