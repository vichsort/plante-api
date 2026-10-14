import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)


def test_correlation_id_middleware_generates_and_propagates():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    def sample():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    generated_id = response.headers["X-Correlation-ID"]
    assert len(generated_id) > 10

    # Propaga o id se enviado no request
    custom_id = "test-correlation-uuid-1234"
    res_custom = client.get("/test", headers={"X-Correlation-ID": custom_id})
    assert res_custom.headers["X-Correlation-ID"] == custom_id


def _correlation_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    def sample():
        return {"ok": True}

    return app


@pytest.mark.parametrize(
    "incoming",
    ["abc", "1-5759e988-bd862e3fe1be46a994272793", "req_ID.v2-01", "a" * 128],
)
def test_correlation_id_accepts_valid_non_uuid_values(incoming):
    response = TestClient(_correlation_app()).get("/test", headers={"X-Correlation-ID": incoming})
    assert response.headers["X-Correlation-ID"] == incoming


@pytest.mark.parametrize(
    "incoming",
    ["a" * 129, "has space", "inject\\nlog", "semi;colon", "<script>", "Root=1-5759e988"],
)
def test_correlation_id_replaces_invalid_values_with_uuid4(incoming):
    response = TestClient(_correlation_app()).get("/test", headers={"X-Correlation-ID": incoming})
    returned = response.headers["X-Correlation-ID"]
    assert returned != incoming
    assert uuid.UUID(returned).version == 4


def test_correlation_id_generates_uuid4_for_empty_header():
    response = TestClient(_correlation_app()).get("/test", headers={"X-Correlation-ID": ""})
    assert uuid.UUID(response.headers["X-Correlation-ID"]).version == 4


def test_security_headers_middleware():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    def sample():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "X-XSS-Protection" not in response.headers
    assert (
        response.headers["Content-Security-Policy"]
        == "default-src 'none'; frame-ancestors 'none'"
    )


@pytest.mark.parametrize("path", ["/docs", "/docs/oauth2-redirect", "/redoc"])
def test_security_headers_skip_csp_on_docs_pages(path):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    response = TestClient(app).get(path)
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"


def test_security_headers_apply_csp_to_openapi_schema():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    response = TestClient(app).get("/openapi.json")
    assert "Content-Security-Policy" in response.headers


def test_rate_limit_middleware_blocks_after_exceeding_limit():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=2)

    @app.get("/api/test")
    def sample():
        return {"ok": True}

    client = TestClient(app)
    
    r1 = client.get("/api/test")
    assert r1.status_code == 200
    r2 = client.get("/api/test")
    assert r2.status_code == 200
    
    r3 = client.get("/api/test")
    assert r3.status_code == 429
    data = r3.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "PLANTE_4029_RATE_LIMIT_EXCEEDED"


def _rate_limited_app(**kwargs) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, **kwargs)

    @app.get("/api/test")
    def general():
        return {"ok": True}

    @app.post("/identify")
    def identify():
        return {"ok": True}

    @app.get("/health/liveness")
    def liveness():
        return {"status": "ok"}

    return app


def test_rate_limit_applies_sensitive_limit_to_identify_route():
    client = TestClient(_rate_limited_app(requests_per_minute=10, sensitive_requests_per_minute=1))

    assert client.post("/identify").status_code == 200
    blocked = client.post("/identify")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["details"]["limit"] == 1
    assert int(blocked.headers["Retry-After"]) >= 1


def test_rate_limit_scopes_are_independent():
    client = TestClient(_rate_limited_app(requests_per_minute=1, sensitive_requests_per_minute=1))

    assert client.get("/api/test").status_code == 200
    assert client.get("/api/test").status_code == 429
    # Esgotar o escopo geral não bloqueia o escopo sensível
    assert client.post("/identify").status_code == 200


def test_rate_limit_skips_exempt_paths():
    client = TestClient(_rate_limited_app(requests_per_minute=1))

    for _ in range(3):
        response = client.get("/health/liveness")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers


class _FakePipeline:
    def __init__(self, store: dict[str, int]) -> None:
        self._store = store
        self._key = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def incr(self, key: str) -> None:
        self._key = key

    def expire(self, key: str, seconds: int) -> None:
        pass

    async def execute(self) -> list:
        self._store[self._key] = self._store.get(self._key, 0) + 1
        return [self._store[self._key], True]


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def pipeline(self, transaction: bool = True) -> _FakePipeline:
        return _FakePipeline(self.store)


def test_rate_limit_uses_redis_counter_when_available():
    fake = _FakeRedis()
    client = TestClient(_rate_limited_app(requests_per_minute=2, redis_provider=lambda: fake))

    assert client.get("/api/test").headers["X-RateLimit-Remaining"] == "1"
    assert client.get("/api/test").status_code == 200
    assert client.get("/api/test").status_code == 429
    assert len(fake.store) == 1
    assert next(iter(fake.store)).startswith("plante:ratelimit:default:")


def test_rate_limit_falls_back_to_memory_when_redis_fails():
    def broken_redis():
        raise ConnectionError("redis down")

    client = TestClient(_rate_limited_app(requests_per_minute=1, redis_provider=broken_redis))

    assert client.get("/api/test").status_code == 200
    assert client.get("/api/test").status_code == 429


def test_rate_limit_sensitive_match_is_exact():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=10, sensitive_requests_per_minute=1)

    @app.post("/identify/confirm")
    def confirm():
        return {"ok": True}

    response = TestClient(app).post("/identify/confirm")
    assert response.headers["X-RateLimit-Limit"] == "10"
