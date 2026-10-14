from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


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
