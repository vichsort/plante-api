import time
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from src.shared.api.response import ApiResponse
from src.shared.domain.exceptions import ExternalServiceError, RateLimitExceededError
from src.shared.domain.value_objects.ids import UserId

log = structlog.stdlib.get_logger()

# Limites padronizados por minuto
_DEFAULT_RATE_LIMIT = 60       # 60 req/min para rotas gerais
_SENSITIVE_RATE_LIMIT = 15     # 15 req/min para rotas de IA e Auth
_WINDOW_SECONDS = 60

# Comparação exata: subrotas baratas (ex: /diagnose/history) seguem o limite geral
_SENSITIVE_PATHS = frozenset({
    "/auth/login",
    "/auth/register",
    "/auth/verify-email",
    "/identify",
    "/diagnose",
})

# Rotas anônimas contam sempre por IP, mesmo com token: senão um token válido escaparia do limite de login
_ANONYMOUS_PATHS = frozenset({
    "/auth/login",
    "/auth/register",
    "/auth/verify-email",
})

_EXEMPT_PATHS = ("/docs", "/openapi.json", "/redoc", "/health/liveness", "/health/readiness")

_KEY_PREFIX = "plante:ratelimit"

T = TypeVar("T")


class CallGuard(Protocol):
    """Circuit breaker injetado pela composição (ex: CircuitBreaker de src/adapters/resilience)."""

    async def call(self, func: Callable[[], Awaitable[T]]) -> T: ...


class WindowCounter(Protocol):
    """Contador compartilhado entre processos (Redis em produção)."""
    async def increment_with_expiry(self, key: str, ttl_seconds: int) -> int: ...


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de Rate Limiting com janela fixa por cliente e escopo (geral / sensível).
    O cliente é o usuário do access token quando há um válido (o CGNAT das operadoras e o
    load balancer colocam muitos usuários no mesmo IP); senão, o IP.
    Usa Redis como contador compartilhado entre workers e cai para um contador
    em memória (por processo) caso o Redis esteja indisponível; com `redis_breaker`, após uma
    falha fica no contador em memória até o breaker liberar, em vez de tentar o Redis a cada requisição.
    Evita abuso de cota em APIs de IA e endpoints sensíveis.
    """
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = _DEFAULT_RATE_LIMIT,
        sensitive_requests_per_minute: int = _SENSITIVE_RATE_LIMIT,
        redis_provider: Callable[[], WindowCounter] | None = None,
        # Dono do access token, ou None se o token for inválido ou expirado
        token_decoder: Callable[[str], UserId | None] | None = None,
        redis_breaker: CallGuard | None = None,
    ) -> None:
        super().__init__(app)
        self._default_limit = requests_per_minute
        self._sensitive_limit = sensitive_requests_per_minute
        self._redis_provider = redis_provider
        self._token_decoder = token_decoder
        self._redis_breaker = redis_breaker
        self._memory_window = 0
        self._memory_counters: dict[str, int] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Pula rate limit para docs e health-checks
        path = request.url.path
        if path.startswith(_EXEMPT_PATHS):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        client = self._client_identity(request, path, client_ip)
        now = time.time()
        window = int(now // _WINDOW_SECONDS)
        retry_after = max(_WINDOW_SECONDS - int(now % _WINDOW_SECONDS), 1)

        # Identifica o limite e o escopo da rota (contadores independentes)
        is_sensitive = path.rstrip("/") in _SENSITIVE_PATHS
        scope = "sensitive" if is_sensitive else "default"
        limit = self._sensitive_limit if is_sensitive else self._default_limit
        key = f"{_KEY_PREFIX}:{scope}:{client}:{window}"

        count = await self._increment(key, window)

        if count > limit:
            log.warning("rate_limit.exceeded", client=client, client_ip=client_ip, path=path, count=count, limit=limit)
            exc = RateLimitExceededError(limit=limit, retry_after_seconds=retry_after)
            envelope = ApiResponse.fail(code=exc.code, message=exc.message, details=exc.details)
            return Response(
                content=envelope.model_dump_json(),
                status_code=exc.status_code,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - count)
        return response

    def _client_identity(self, request: Request, path: str, client_ip: str) -> str:
        if self._token_decoder is not None and path.rstrip("/") not in _ANONYMOUS_PATHS:
            scheme, _, token = request.headers.get("authorization", "").partition(" ")
            if scheme.lower() == "bearer" and token:
                owner = self._token_decoder(token)
                if owner is not None:
                    return f"user:{owner}"
                # Token inválido ou expirado: a rota responde 401, aqui conta pelo IP
        return f"ip:{client_ip}"

    async def _increment(self, key: str, window: int) -> int:
        provider = self._redis_provider
        if provider is not None:
            try:
                if self._redis_breaker is None:
                    return await _increment_in_redis(provider, key)
                return await self._redis_breaker.call(lambda: _increment_in_redis(provider, key))
            except ExternalServiceError as exc:
                # Falha ou backoff ativo: o breaker loga a abertura e o fechamento. Comando
                # recusado não abre o breaker, então é logado aqui
                if not exc.retryable:
                    log.error("rate_limit.redis_rejected", error=str(exc))
            except Exception as exc:
                # Rate limit nunca derruba a requisição
                log.warning("rate_limit.redis_unavailable", error=str(exc))

        return self._increment_in_memory(key, window)

    def _increment_in_memory(self, key: str, window: int) -> int:
        # Descarta contadores de janelas anteriores para não crescer indefinidamente
        if window != self._memory_window:
            self._memory_window = window
            self._memory_counters.clear()

        self._memory_counters[key] = self._memory_counters.get(key, 0) + 1
        return self._memory_counters[key]


async def _increment_in_redis(provider: Callable[[], WindowCounter], key: str) -> int:
    return await provider().increment_with_expiry(key, ttl_seconds=_WINDOW_SECONDS * 2)
