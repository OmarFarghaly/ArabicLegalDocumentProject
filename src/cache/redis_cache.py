"""Redis cache for the RAG app (cache-aside, fails open).

If Redis is down or slow, `get` returns None and `set` does nothing, so the
app keeps working, just without the cache.
"""

import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError


class Cache(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...


def normalize_query(text: str) -> str:
    """Make trivially different questions share one cache entry."""
    return re.sub(r"\s+", " ", text).strip().lower()


def make_key(prefix: str, query: str, **params: Any) -> str:
    """Build a key from the query and everything that changes the answer.

    Put the models, limits and collection in `params`: when any of them
    changes, the key changes and old answers are not reused.
    """
    raw = json.dumps(
        {"q": normalize_query(query), **params}, sort_keys=True, ensure_ascii=False
    )
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


class RedisCache:
    def __init__(self, client: Redis, default_ttl: int = 3600):
        self.client = client
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self.client.get(key)
        except RedisError:
            return None
        return None if raw is None else json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            await self.client.set(
                key, json.dumps(value, ensure_ascii=False), ex=ttl or self.default_ttl
            )
        except RedisError:
            pass


async def get_or_compute(
    cache: Cache,
    key: str,
    compute: Callable[[], Awaitable[Any]],
    ttl: int | None = None,
) -> Any:
    """Return the cached value, or compute and store it (never stores empty)."""
    hit = await cache.get(key)
    if hit is not None:
        return hit
    value = await compute()
    if value:
        await cache.set(key, value, ttl)
    return value
