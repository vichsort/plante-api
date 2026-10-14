import time
from collections.abc import Callable

import structlog
from fastapi import Request
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from src.api.response import ApiResponse
from src.domain.exceptions import RateLimitExceededError

log = structlog.get_logger()

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

_EXEMPT_PATHS = ("/docs", "/openapi.json", "/redoc", "/healthz")

_KEY_PREFIX = "plante:ratelimit"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de Rate Limiting com janela fixa por IP e escopo (geral / sensível).
    Usa Redis como contador compartilhado entre workers e cai para um contador
    em memória (por processo) caso o Redis esteja indisponível.
    Evita abuso de cota em APIs de IA e endpoints sensíveis.
    """
    def __init__(
        self,
        app,
        requests_per_minute: int = _DEFAULT_RATE_LIMIT,
        sensitive_requests_per_minute: int = _SENSITIVE_RATE_LIMIT,
        redis_provider: Callable[[], Redis] | None = None,
    ) -> None:
        super().__init__(app)
        self._default_limit = requests_per_minute
        self._sensitive_limit = sensitive_requests_per_minute
        self._redis_provider = redis_provider
        self._memory_window = 0
        self._memory_counters: dict[str, int] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Pula rate limit para docs e health-checks
        path = request.url.path
        if path.startswith(_EXEMPT_PATHS):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = int(now // _WINDOW_SECONDS)
        retry_after = max(_WINDOW_SECONDS - int(now % _WINDOW_SECONDS), 1)

        # Identifica o limite e o escopo da rota (contadores independentes)
        is_sensitive = path.rstrip("/") in _SENSITIVE_PATHS
        scope = "sensitive" if is_sensitive else "default"
        limit = self._sensitive_limit if is_sensitive else self._default_limit
        key = f"{_KEY_PREFIX}:{scope}:{client_ip}:{window}"

        count = await self._increment(key, window)

        if count > limit:
            log.warning("rate_limit.exceeded", client_ip=client_ip, path=path, count=count, limit=limit)
            exc = RateLimitExceededError(limit=limit, retry_after_seconds=retry_after)
            envelope = ApiResponse.fail(code=exc.code, message=exc.message, details=exc.details)
            return JSONResponse(
                status_code=exc.status_code,
                content=envelope.model_dump(),
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

    async def _increment(self, key: str, window: int) -> int:
        if self._redis_provider is not None:
            try:
                redis = self._redis_provider()
                async with redis.pipeline(transaction=True) as pipe:
                    pipe.incr(key)
                    pipe.expire(key, _WINDOW_SECONDS * 2)
                    count, _ = await pipe.execute()
                return int(count)
            except Exception as exc:
                log.warning("rate_limit.redis_unavailable", error=str(exc))

        return self._increment_in_memory(key, window)

    def _increment_in_memory(self, key: str, window: int) -> int:
        # Descarta contadores de janelas anteriores para não crescer indefinidamente
        if window != self._memory_window:
            self._memory_window = window
            self._memory_counters.clear()

        self._memory_counters[key] = self._memory_counters.get(key, 0) + 1
        return self._memory_counters[key]
