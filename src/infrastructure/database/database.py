"""
Database connection management module.
"""
import typing as t
import contextlib
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import get_settings

# Create async engine using settings
settings = get_settings()
engine: AsyncEngine = create_async_engine(
    settings.db.url,
    echo=settings.db.echo,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
    pool_timeout=settings.db.pool_timeout,
    pool_recycle=settings.db.pool_recycle,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


@asynccontextmanager
async def get_db_session() -> t.AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as an async context manager.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncSession:
    """
    Get a database session.
    
    Returns:
        An AsyncSession instance
    
    Note:
        The caller is responsible for committing, rolling back, and closing the session.
    """
    return async_session_factory()


async def get_db_connection() -> AsyncConnection:
    """
    Get a raw database connection for special operations.
    """
    async with engine.begin() as conn:
        return conn


async def init_db() -> None:
    """
    Initialize database tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 