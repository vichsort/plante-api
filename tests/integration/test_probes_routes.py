import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.bootstrap.probes import ReadinessCache, readiness_cache


@pytest.fixture(autouse=True)
def _clear_readiness_cache():
    readiness_cache.clear()
    yield
    readiness_cache.clear()


def _healthy_engine() -> MagicMock:
    conn = AsyncMock()
    engine = MagicMock()
    engine.connect.return_value.__aenter__.return_value = conn
    return engine


def test_liveness_route(client: TestClient):
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "alive"}


def test_readiness_route_ready(client: TestClient):
    container = client.app.state.container
    redis = AsyncMock()

    with container.infra.engine.override(_healthy_engine()), container.adapters.redis.override(redis):
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ready", "checks": {"database": True, "redis": True}}
    redis.ping.assert_awaited_once()


def test_readiness_route_not_ready_when_redis_down(client: TestClient):
    container = client.app.state.container
    redis = AsyncMock()
    redis.ping.side_effect = ConnectionError("redis down")

    with container.infra.engine.override(_healthy_engine()), container.adapters.redis.override(redis):
        response = client.get("/health/readiness")

    assert response.status_code == 503
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "PLANTE_5003_SERVICE_NOT_READY"
    assert payload["error"]["details"]["checks"] == {"database": True, "redis": False}


def test_readiness_route_caches_result(client: TestClient):
    container = client.app.state.container
    redis = AsyncMock()

    with container.infra.engine.override(_healthy_engine()), container.adapters.redis.override(redis):
        for _ in range(3):
            assert client.get("/health/readiness").status_code == 200

    redis.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_readiness_cache_shares_inflight_check():
    cache = ReadinessCache()
    calls = 0
    release = asyncio.Event()

    async def compute():
        nonlocal calls
        calls += 1
        await release.wait()
        return {"database": True, "redis": True}

    waiters = [asyncio.create_task(cache.get(compute)) for _ in range(5)]
    await asyncio.sleep(0)
    release.set()
    results = await asyncio.gather(*waiters)

    assert calls == 1
    assert all(r == {"database": True, "redis": True} for r in results)
