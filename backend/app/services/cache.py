"""
Redis caching helpers with TTL management.

Provides typed get/set operations with automatic JSON serialization
and predefined TTL policies for each data type.
"""

import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.dependencies import get_redis

logger = logging.getLogger("smv.cache")

# ──────────────────────────────────────────────
# TTL Policies (seconds)
# ──────────────────────────────────────────────

TTL_SNAPSHOT = 300          # 5 minutes — ticker snapshots
TTL_AGGREGATES = 86400      # 24 hours  — historical OHLCV bars
TTL_HISTORY = 604800        # 7 days    — extended ticker history
TTL_SENTIMENT = 3600        # 1 hour    — news sentiment scores


# ──────────────────────────────────────────────
# Key builders
# ──────────────────────────────────────────────

def key_snapshot(ticker: str) -> str:
    return f"polygon:snapshot:{ticker.upper()}"


def key_aggregates(ticker: str, timespan: str, date_from: str, date_to: str) -> str:
    return f"polygon:aggs:{ticker.upper()}:{timespan}:{date_from}:{date_to}"


def key_history(ticker: str, range_: str) -> str:
    return f"polygon:history:{ticker.upper()}:{range_}"


def key_sentiment(industry: str) -> str:
    return f"news:sentiment:{industry.lower().replace(' ', '_')}"


# ──────────────────────────────────────────────
# Cache operations
# ──────────────────────────────────────────────

async def cache_get(key: str) -> Any | None:
    """Get a value from Redis, deserializing JSON. Returns None on miss."""
    redis = get_redis()
    raw = await redis.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def cache_set(key: str, value: Any, ttl: int) -> None:
    """Set a value in Redis with a TTL, serializing to JSON."""
    redis = get_redis()
    serialized = json.dumps(value, default=str)
    await redis.setex(key, ttl, serialized)
    logger.debug(f"Cache SET {key} (TTL={ttl}s)")


async def cache_delete(key: str) -> None:
    """Delete a key from Redis."""
    redis = get_redis()
    await redis.delete(key)


async def cache_get_or_fetch(
    key: str,
    ttl: int,
    fetch_fn,
) -> Any:
    """
    Cache-aside pattern: return cached value if present,
    otherwise call fetch_fn(), cache the result, and return it.
    """
    cached = await cache_get(key)
    if cached is not None:
        logger.debug(f"Cache HIT {key}")
        return cached

    logger.debug(f"Cache MISS {key} — fetching...")
    result = await fetch_fn()
    if result is not None:
        await cache_set(key, result, ttl)
    return result
