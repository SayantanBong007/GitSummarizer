from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        engine_kwargs: dict = {
            "pool_pre_ping": True,
            "echo": not settings.is_production,
        }
        # pool_size/max_overflow are QueuePool-only kwargs. SQLite (used by the test
        # suite via DATABASE_URL=sqlite+aiosqlite:///:memory:) uses StaticPool, which
        # rejects them outright with a TypeError.
        if not settings.database_url.startswith("sqlite"):
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20
        _engine = create_async_engine(settings.database_url, **engine_kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_db_session() as session:
        yield session


def reset_engine() -> None:
    """Synchronously discard the module-level engine and session factory.

    Called BEFORE asyncio.run() in Celery prefork tasks so the new event loop
    starts with a fresh engine instead of inheriting connections attached to the
    previous (now-closed) loop — which would cause 'Future attached to a
    different loop' errors.
    """
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        with suppress(Exception):
            await _engine.dispose()
        _engine = None
    _session_factory = None
