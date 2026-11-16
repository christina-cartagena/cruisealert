"""Async SQLAlchemy engine, session factory, and declarative base."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# On serverless (Vercel sets $VERCEL=1), each invocation is short-lived and may
# hit a PgBouncer-pooled endpoint (e.g. Neon's -pooler host). Use NullPool and
# disable asyncpg's prepared-statement cache so pooled connections don't break.
_IS_SERVERLESS = bool(os.getenv("VERCEL"))

if _IS_SERVERLESS:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
        # statement_cache_size=0 is required behind Neon's PgBouncer pooler;
        # ssl=True satisfies Neon's required-SSL connections.
        connect_args={"statement_cache_size": 0, "ssl": True},
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.ENVIRONMENT == "development",
    )

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped async session."""
    async with AsyncSessionLocal() as session:
        yield session
