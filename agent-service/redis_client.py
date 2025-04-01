"""
Redis client module for BazaarOps agent-service.

Provides sync and async Redis clients for:
- Pub/Sub messaging (event-driven architecture)
- Conversation context caching (with TTL)
- General key-value caching
"""

import os
import logging
import redis
import redis.asyncio as aioredis
from redis.connection import ConnectionPool
from redis.asyncio.connection import ConnectionPool as AsyncConnectionPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# ---------------------------------------------------------------------------
# Connection pools (created once, reused across requests)
# ---------------------------------------------------------------------------

_sync_pool: ConnectionPool | None = None
_async_pool: AsyncConnectionPool | None = None


def _get_sync_pool() -> ConnectionPool:
    global _sync_pool
    if _sync_pool is None:
        _sync_pool = ConnectionPool.from_url(
            REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _sync_pool


def _get_async_pool() -> AsyncConnectionPool:
    global _async_pool
    if _async_pool is None:
        _async_pool = aioredis.ConnectionPool.from_url(
            REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _async_pool


# ---------------------------------------------------------------------------
# Client accessors
# ---------------------------------------------------------------------------

def get_sync_client() -> redis.Redis:
    """Return a synchronous Redis client backed by the shared connection pool."""
    return redis.Redis(connection_pool=_get_sync_pool())


def get_async_client() -> aioredis.Redis:
    """Return an async Redis client backed by the shared connection pool."""
    return aioredis.Redis(connection_pool=_get_async_pool())


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def check_connection() -> bool:
    """
    Ping Redis synchronously.

    Returns True if the connection is healthy, False otherwise.
    Logs a warning (not an exception) on failure so callers can degrade
    gracefully.
    """
    try:
        client = get_sync_client()
        client.ping()
        logger.info("✅ Redis connection healthy: %s", REDIS_URL)
        return True
    except redis.ConnectionError as exc:
        logger.warning("⚠️  Redis connection failed: %s", exc)
        return False
    except Exception as exc:  # pragma: no cover
        logger.warning("⚠️  Redis unexpected error: %s", exc)
        return False


async def async_check_connection() -> bool:
    """Async variant of check_connection."""
    try:
        client = get_async_client()
        await client.ping()
        logger.info("✅ Redis async connection healthy: %s", REDIS_URL)
        return True
    except Exception as exc:
        logger.warning("⚠️  Redis async connection failed: %s", exc)
        return False
