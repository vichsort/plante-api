import asyncio
import time
import uuid
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.bootstrap.container import Container
from src.modules.identity.adapters.security.jwt_token_service import JwtTokenService
from src.modules.identity.domain.ports.token_service import TokenKind
from src.shared.adapters import CircuitBreaker, RedisClient
from src.shared.api import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    WindowCounter,
)
from src.shared.domain import InternalError, ServiceUnavailableError, UserId


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
    assert data["error"]["code"] == "PLANTE_4050_RATE_LIMIT_EXCEEDED"


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


class _FakeRedis(WindowCounter):
    """
    Contador em memória para a lógica do rate limit. O contrato do contador real (INCR + EXPIRE
    no Redis) é testado em `tests/integration/cache/test_redis_client.py`.
    """
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def increment_with_expiry(self, key: str, ttl_seconds: int) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]


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


def _fake_decoder(token: str) -> str | None:
    return token.removeprefix("valid-") if token.startswith("valid-") else None


def _auth(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer valid-{user}"}


def _per_user_app() -> TestClient:
    app = _rate_limited_app(requests_per_minute=1, sensitive_requests_per_minute=1, token_decoder=_fake_decoder)

    @app.post("/auth/login")
    def login():
        return {"ok": True}

    return TestClient(app)


def test_rate_limit_counts_authenticated_users_separately_on_same_ip():
    client = _per_user_app()

    assert client.get("/api/test", headers=_auth("alice")).status_code == 200
    assert client.get("/api/test", headers=_auth("alice")).status_code == 429
    # Mesmo IP (CGNAT / load balancer), outro usuário: contador próprio
    assert client.get("/api/test", headers=_auth("bob")).status_code == 200
    # Anônimo no mesmo IP também não é afetado pelos usuários
    assert client.get("/api/test").status_code == 200


def test_rate_limit_anonymous_routes_count_by_ip_even_with_token():
    client = _per_user_app()

    assert client.post("/auth/login", headers=_auth("alice")).status_code == 200
    # Trocar de token não escapa do limite de login
    assert client.post("/auth/login", headers=_auth("bob")).status_code == 429


def test_rate_limit_invalid_token_counts_by_ip():
    client = _per_user_app()

    assert client.get("/api/test", headers={"Authorization": "Bearer forged"}).status_code == 200
    assert client.get("/api/test").status_code == 429


def test_rate_limit_redis_key_uses_user_identity():
    fake = _FakeRedis()
    app = _rate_limited_app(redis_provider=lambda: fake, token_decoder=_fake_decoder)

    TestClient(app).get("/api/test", headers=_auth("alice"))
    assert next(iter(fake.store)).startswith("plante:ratelimit:default:user:alice:")


_TEST_SECRET = "test-secret-key-with-at-least-32-bytes"


def test_rate_limit_with_real_token_decoder():
    # O decodificador do app (`src.main`) com o JwtTokenService de verdade
    tokens = JwtTokenService(secret_key=_TEST_SECRET, algorithm="HS256")
    fake = _FakeRedis()
    client = TestClient(_rate_limited_app(redis_provider=lambda: fake, token_decoder=tokens.owner_of))
    user_id = UserId(uuid.uuid4())
    access = tokens.issue(user_id, TokenKind.ACCESS, timedelta(minutes=5))
    refresh = tokens.issue(user_id, TokenKind.REFRESH, timedelta(minutes=5))

    client.get("/api/test", headers={"Authorization": f"Bearer {access}"})
    client.get("/api/test", headers={"Authorization": f"Bearer {refresh}"})
    assert {key.split(":")[3] for key in fake.store} == {"user", "ip"}


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_rate_limit_backs_off_redis_after_failure():
    calls = []
    clock = _Clock()
    fake = _FakeRedis()

    class _FlakyRedis:
        async def increment_with_expiry(self, key: str, ttl_seconds: int) -> int:
            calls.append(clock.now)
            if len(calls) == 1:
                # RedisClient contract: a connection failure is a ServiceUnavailableError
                raise ServiceUnavailableError()
            return await fake.increment_with_expiry(key, ttl_seconds)

    flaky = _FlakyRedis()

    def flaky_redis():
        return flaky

    client = TestClient(_rate_limited_app(
        requests_per_minute=100,
        redis_provider=flaky_redis,
        redis_breaker=CircuitBreaker("Redis", failure_threshold=1, recovery_timeout_seconds=30, clock=clock),
    ))

    for _ in range(3):
        assert client.get("/api/test").status_code == 200
    # Só a primeira requisição tentou o Redis; as demais usaram a memória durante o backoff
    assert len(calls) == 1

    clock.now = 30
    assert client.get("/api/test").status_code == 200
    assert len(calls) == 2
    assert len(fake.store) == 1


def test_rate_limit_falls_back_on_unexpected_redis_error():
    def buggy_redis():
        raise RuntimeError("unexpected")

    client = TestClient(_rate_limited_app(requests_per_minute=1, redis_provider=buggy_redis))

    assert client.get("/api/test").status_code == 200
    assert client.get("/api/test").status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_does_not_hang_on_unresponsive_redis():
    # Servidor que aceita a conexão e nunca responde: simula Redis travado
    async def never_reply(reader, writer):
        while await reader.read(1024):
            pass
        writer.close()

    server = await asyncio.start_server(never_reply, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    redis = RedisClient.from_url(f"redis://127.0.0.1:{port}", socket_timeout=0.2, socket_connect_timeout=0.2)
    app = _rate_limited_app(redis_provider=lambda: redis, redis_breaker=CircuitBreaker("Redis", failure_threshold=1))

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            started = time.monotonic()
            assert (await client.get("/api/test")).status_code == 200
            assert time.monotonic() - started < 1.0
            # Backoff: a segunda requisição nem tenta o Redis
            started = time.monotonic()
            assert (await client.get("/api/test")).status_code == 200
            assert time.monotonic() - started < 0.1
    finally:
        await redis.close()
        server.close()
        await server.wait_closed()


def test_container_redis_client_has_short_timeouts():
    redis = Container().adapters.redis()
    kwargs = redis._redis.connection_pool.connection_kwargs
    assert kwargs["socket_timeout"] == 0.5
    assert kwargs["socket_connect_timeout"] == 0.5


class _RejectingRedis(WindowCounter):
    async def increment_with_expiry(self, key: str, ttl_seconds: int) -> int:
        # RedisClient contract: a refused command (WRONGTYPE) is an InternalError, logged by the client
        raise InternalError()


def test_rate_limit_falls_back_to_memory_when_redis_rejects_command():
    client = TestClient(_rate_limited_app(requests_per_minute=1, redis_provider=_RejectingRedis))

    assert client.get("/api/test").status_code == 200
    assert client.get("/api/test").status_code == 429
