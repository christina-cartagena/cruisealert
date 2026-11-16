"""Pytest fixtures.

Pure unit tests (alert engine, scraper delta-check, auth crypto/JWT) need no
database and always run. DB-backed integration tests depend on the ``db_session``
fixture, which connects to a TEST database and wraps each test in a transaction
that is rolled back afterward. If no test database is reachable, those tests are
skipped (never run against production).

Set TEST_DATABASE_URL to point at a disposable database, e.g. the local Docker
Postgres from docker-compose.yml.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cruisealert:cruisealert@localhost:5432/cruisealert_test",
)


@pytest_asyncio.fixture(scope="session")
async def _engine():
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.connect():
            pass
    except Exception:  # noqa: BLE001 - no DB available; DB tests will skip
        await engine.dispose()
        pytest.skip("No test database reachable", allow_module_level=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine) -> AsyncSession:
    """Per-test session wrapped in a transaction that is rolled back."""
    connection = await _engine.connect()
    trans = await connection.begin()
    factory = async_sessionmaker(bind=connection, expire_on_commit=False, class_=AsyncSession)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()
