import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from main import health


def make_request(point_count: int = 1, redis_enabled: bool = True):
    qdrant_client = SimpleNamespace(
        count=AsyncMock(return_value=SimpleNamespace(count=point_count))
    )
    semantic_cache = (
        SimpleNamespace(client=SimpleNamespace(ping=AsyncMock(return_value=True)))
        if redis_enabled
        else None
    )
    llm = SimpleNamespace(health_check=AsyncMock(return_value=True))
    state = SimpleNamespace(
        config=SimpleNamespace(COLLECTION_NAME="test_collection"),
        qdrant_reterival=SimpleNamespace(client=qdrant_client),
        semantic_cache=semantic_cache,
        llm=llm,
    )
    return SimpleNamespace(app=SimpleNamespace(state=state)), state


def test_health_reports_healthy_dependencies():
    request, state = make_request()

    response = asyncio.run(health(request))

    assert response == {
        "status": "healthy",
        "checks": {"qdrant": "healthy", "redis": "healthy", "vllm": "healthy"},
    }
    state.qdrant_reterival.client.count.assert_awaited_once_with(
        collection_name="test_collection",
        exact=False,
    )


def test_health_returns_503_when_index_is_empty():
    request, _ = make_request(point_count=0)

    with pytest.raises(HTTPException) as error:
        asyncio.run(health(request))

    assert error.value.status_code == 503
    assert error.value.detail["checks"]["qdrant"] == "unhealthy"


def test_health_skips_redis_when_cache_is_disabled():
    request, _ = make_request(redis_enabled=False)

    response = asyncio.run(health(request))

    assert response["checks"]["redis"] == "disabled"
