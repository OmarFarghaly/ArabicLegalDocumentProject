import fakeredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from src.api.versions.v1 import rag
from src.cache import RedisCache

PAYLOAD = {
    "article_number": 147,
    "ar_text": "العقد شريعة المتعاقدين",
    "text_en": "The contract is the law of the parties",
    "book": None,
    "chapter": None,
    "section": None,
    "topic": None,
    "is_repealed": False,
    "source_page": 52,
    "citation": "Egyptian Civil Code, Article 147",
}


class FakePoint:
    def __init__(self, payload):
        self.payload = payload


class FakeRetrieval:
    def __init__(self, points=None):
        self.calls = 0
        self.points = [FakePoint(PAYLOAD)] if points is None else points

    async def search(self, **kwargs):
        self.calls += 1
        return self.points


class FakeReranker:
    def rerank(self, query, payloads, lang, limit):
        return payloads


def make_app(monkeypatch, cache, retrieval=None):
    monkeypatch.setattr(rag, "detect", lambda text: "en")
    app = FastAPI()
    app.include_router(rag.rag_router)
    app.state.qdrant_reterival = retrieval or FakeRetrieval()
    app.state.reranker = FakeReranker()
    app.state.cache = cache
    return app


def fake_cache():
    return RedisCache(fakeredis.FakeAsyncRedis(decode_responses=True))


def ask(client, question):
    return client.post("/api/v1/rag/answer", json={"question": question})


def test_second_identical_question_is_served_from_cache(monkeypatch):
    app = make_app(monkeypatch, fake_cache())
    with TestClient(app) as client:
        first = ask(client, "What is a contract?")
        second = ask(client, "  what is a   CONTRACT? ")
    assert first.json() == second.json()
    assert app.state.qdrant_reterival.calls == 1


def test_different_question_searches_again(monkeypatch):
    app = make_app(monkeypatch, fake_cache())
    with TestClient(app) as client:
        ask(client, "What is a contract?")
        ask(client, "What is a lease?")
    assert app.state.qdrant_reterival.calls == 2


def test_cache_disabled_always_searches(monkeypatch):
    app = make_app(monkeypatch, None)
    with TestClient(app) as client:
        ask(client, "What is a contract?")
        ask(client, "What is a contract?")
    assert app.state.qdrant_reterival.calls == 2


def test_redis_down_still_answers(monkeypatch):
    class BrokenRedis:
        async def get(self, key):
            raise RedisConnectionError("down")

        async def set(self, *args, **kwargs):
            raise RedisConnectionError("down")

    app = make_app(monkeypatch, RedisCache(BrokenRedis()))
    with TestClient(app) as client:
        response = ask(client, "What is a contract?")
    assert response.status_code == 200
    assert response.json()["outputs"][0]["article_number"] == 147