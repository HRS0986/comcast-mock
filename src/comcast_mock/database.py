import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from comcast_mock.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None
db_connected: bool = False


def build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )


def init_engine() -> None:
    global engine, session_factory
    if engine is None:
        engine = build_engine()
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )


async def dispose_engine() -> None:
    global engine, db_connected
    if engine is not None:
        await engine.dispose()
        engine = None
        db_connected = False


async def get_session() -> AsyncIterator[AsyncSession]:
    if session_factory is None:
        raise RuntimeError("Database engine has not been initialized")
    async with session_factory() as session:
        yield session
