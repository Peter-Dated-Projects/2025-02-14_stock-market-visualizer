"""
Database connection factories and FastAPI dependency injectors.

Provides async connections to MySQL (SQLAlchemy), MongoDB (Motor), and Redis.
All connections are initialized in the app lifespan and torn down on shutdown.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.config import settings


# ──────────────────────────────────────────────
# MySQL (SQLAlchemy Async)
# ──────────────────────────────────────────────

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_mysql() -> None:
    """Create the async engine and session factory. Called once at startup."""
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.mysql_url,
        echo=settings.is_staging,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_mysql() -> None:
    """Dispose the engine connection pool. Called on shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_mysql() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async MySQL session."""
    if _session_factory is None:
        raise RuntimeError("MySQL not initialized. Call init_mysql() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ──────────────────────────────────────────────
# MongoDB (Motor Async)
# ──────────────────────────────────────────────

_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None


def init_mongo() -> None:
    """Create the Motor client. Called once at startup."""
    global _mongo_client, _mongo_db
    _mongo_client = AsyncIOMotorClient(settings.mongo_url)
    _mongo_db = _mongo_client[settings.mongo_database]


async def close_mongo() -> None:
    """Close the Motor client. Called on shutdown."""
    global _mongo_client, _mongo_db
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None


def get_mongo() -> AsyncIOMotorDatabase:
    """FastAPI dependency — returns the MongoDB database handle."""
    if _mongo_db is None:
        raise RuntimeError("MongoDB not initialized. Call init_mongo() first.")
    return _mongo_db


# ──────────────────────────────────────────────
# Redis (async)
# ──────────────────────────────────────────────

_redis: Redis | None = None


def init_redis() -> None:
    """Create the async Redis client. Called once at startup."""
    global _redis
    _redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
    )


async def close_redis() -> None:
    """Close the Redis connection pool. Called on shutdown."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis:
    """FastAPI dependency — returns the async Redis client."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis
