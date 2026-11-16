"""Alembic environment.

Migrations run **synchronously** (psycopg2). The application itself is async
(asyncpg), but asyncpg prepares every statement and so cannot execute the
multi-statement schema SQL in one shot — psycopg2's simple-query protocol can.
We therefore rewrite the ``+asyncpg`` URL to ``+psycopg2`` for migrations only.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app import models  # noqa: F401 - registers all tables on Base.metadata


def _sync_url() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")


config = context.config
config.set_main_option("sqlalchemy.url", _sync_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
