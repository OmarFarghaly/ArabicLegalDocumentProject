"""Semantic cache on top of Redis Stack (RediSearch vector index).

One index per language, because the Arabic and English embedding models can
have different dimensions. The index is created lazily on the first `set`,
using the length of the vector, so no dimension has to be configured.
"""

import hashlib

import numpy as np
from loguru import logger
from redis.asyncio import Redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query


def _s(value) -> str:
    """Redis returns bytes when decode_responses is False."""
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _to_bytes(vec) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


class SemanticCache:
    def __init__(self, client: Redis, ttl: int, threshold: float):
        # The client must NOT use decode_responses=True (embeddings are bytes).
        self.client = client
        self.ttl = ttl
        self.threshold = threshold
        self._ready: set[str] = set()

    @staticmethod
    def _index(lang: str) -> str:
        return f"semantic_cache_{lang}"

    async def ensure_index(self, lang: str, dim: int) -> None:
        if lang in self._ready:
            return
        index = self._index(lang)
        try:
            await self.client.ft(index).info()
        except Exception:
            schema = (
                TextField("query"),
                TextField("answer"),
                VectorField(
                    "embedding",
                    "HNSW",
                    {"TYPE": "FLOAT32", "DIM": dim, "DISTANCE_METRIC": "COSINE"},
                ),
            )
            await self.client.ft(index).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=[f"sc:{lang}:"], index_type=IndexType.HASH
                ),
            )
        self._ready.add(lang)

    async def get(self, lang: str, vec) -> str | None:
        """Return the cached answer if a close enough question exists."""
        try:
            query = (
                Query("*=>[KNN 1 @embedding $v AS dist]")
                .return_fields("answer", "dist")
                .dialect(2)
            )
            result = await self.client.ft(self._index(lang)).search(
                query, query_params={"v": _to_bytes(vec)}
            )
            if result.docs and float(_s(result.docs[0].dist)) <= self.threshold:
                logger.info("semantic cache hit (lang={})", lang)
                return _s(result.docs[0].answer)
        except Exception as exc:  # the cache must never break the API
            logger.warning("semantic cache get failed: {}", exc)
        return None

    async def set(self, lang: str, query: str, vec, answer: str) -> None:
        try:
            await self.ensure_index(lang, len(vec))
            key = f"sc:{lang}:{hashlib.sha256(query.encode('utf-8')).hexdigest()}"
            await self.client.hset(
                key,
                mapping={
                    "query": query,
                    "answer": answer,
                    "embedding": _to_bytes(vec),
                },
            )
            await self.client.expire(key, self.ttl)
        except Exception as exc:
            logger.warning("semantic cache set failed: {}", exc)