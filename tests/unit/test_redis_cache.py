import asyncio

import fakeredis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.cache import RedisCache, get_or_compute, make_key, normalize_query


def run(coro):
    return asyncio.run(coro)


def test_normalize_query_collapses_spaces_and_case():
    assert normalize_query("  What  IS a\n contract? ") == "what is a contract?"


def test_same_question_same_key_different_params_different_key():
    a = make_key("rag:v1", "ما هو العقد؟  ", limit=10)
    assert a == make_key("rag:v1", "ما هو العقد؟", limit=10)
    assert a != make_key("rag:v1", "ما هو العقد؟", limit=20)
    assert a.startswith("rag:v1:")


def test_set_then_get_roundtrip_keeps_arabic():
    async def scenario():
        cache = RedisCache(fakeredis.FakeAsyncRedis(decode_responses=True))
        await cache.set("k", {"text": "العقد شريعة المتعاقدين"})
        return await cache.get("k")

    assert run(scenario()) == {"text": "العقد شريعة المتعاقدين"}


def test_missing_key_returns_none():
    cache = RedisCache(fakeredis.FakeAsyncRedis(decode_responses=True))
    assert run(cache.get("nope")) is None


def test_entry_gets_a_ttl():
    async def scenario():
        client = fakeredis.FakeAsyncRedis(decode_responses=True)
        await RedisCache(client, default_ttl=60).set("k", [1])
        return await client.ttl("k")

    assert 0 < run(scenario()) <= 60


def test_get_or_compute_computes_once():
    calls = []

    async def compute():
        calls.append(1)
        return [{"article_number": 147}]

    async def scenario():
        cache = RedisCache(fakeredis.FakeAsyncRedis(decode_responses=True))
        first = await get_or_compute(cache, "k", compute)
        second = await get_or_compute(cache, "k", compute)
        return first, second

    first, second = run(scenario())
    assert first == second == [{"article_number": 147}]
    assert len(calls) == 1


def test_empty_results_are_not_cached():
    calls = []

    async def compute():
        calls.append(1)
        return []

    async def scenario():
        cache = RedisCache(fakeredis.FakeAsyncRedis(decode_responses=True))
        await get_or_compute(cache, "k", compute)
        await get_or_compute(cache, "k", compute)

    run(scenario())
    assert len(calls) == 2


class BrokenRedis:
    async def get(self, key):
        raise RedisConnectionError("down")

    async def set(self, *args, **kwargs):
        raise RedisConnectionError("down")


def test_redis_down_fails_open():
    async def compute():
        return ["fresh"]

    cache = RedisCache(BrokenRedis())
    assert run(cache.get("k")) is None
    assert run(cache.set("k", 1)) is None
    assert run(get_or_compute(cache, "k", compute)) == ["fresh"]
