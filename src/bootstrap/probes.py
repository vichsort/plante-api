import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

import structlog
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.bootstrap.container import Container
from src.shared.adapters import RedisClient
from src.shared.api import ApiResponse, error_responses
from src.shared.domain import JsonObject, ServiceUnavailableError

log = structlog.stdlib.get_logger()

_CHECK_TIMEOUT_SECONDS = 2.0
_READINESS_CACHE_TTL_SECONDS = 5.0


class ReadinessCache:
    """
    Cache curto + single-flight do resultado do readiness.
    Chamadas em loop (rota pública e sem rate limit) não abrem uma conexão
    com Postgres/Redis por requisição: no máximo uma verificação por TTL.
    """
    def __init__(self, ttl_seconds: float = _READINESS_CACHE_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._checks: dict[str, bool] | None = None
        self._expires_at = 0.0
        self._inflight: asyncio.Future[dict[str, bool]] | None = None

    async def get(self, compute: Callable[[], Awaitable[dict[str, bool]]]) -> dict[str, bool]:
        if self._checks is not None and time.monotonic() < self._expires_at:
            return self._checks
        if self._inflight is None:
            self._inflight = asyncio.ensure_future(self._refresh(compute))
        return await asyncio.shield(self._inflight)

    def clear(self) -> None:
        self._checks = None
        self._expires_at = 0.0

    async def _refresh(self, compute: Callable[[], Awaitable[dict[str, bool]]]) -> dict[str, bool]:
        try:
            checks = await compute()
            self._checks = checks
            self._expires_at = time.monotonic() + self._ttl
            return checks
        finally:
            self._inflight = None


readiness_cache = ReadinessCache()

router = APIRouter(prefix="/health", tags=["infra"])


class LivenessResponse(BaseModel):
    status: Literal["alive"] = "alive"


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
    checks: dict[str, bool]


@router.get("/liveness", status_code=200, response_model=ApiResponse[LivenessResponse])
async def liveness() -> ApiResponse[LivenessResponse]:
    """Processo está de pé. Não verifica dependências externas."""
    return ApiResponse.success(LivenessResponse())


@router.get(
    "/readiness",
    status_code=200,
    response_model=ApiResponse[ReadinessResponse],
    responses=error_responses(ServiceUnavailableError),
)
@inject
async def readiness(
    engine: Annotated[AsyncEngine, Depends(Provide[Container.infra.engine])],
    redis: Annotated[RedisClient, Depends(Provide[Container.adapters.redis])],
) -> ApiResponse[ReadinessResponse]:
    """Instância pronta para receber tráfego: Postgres e Redis respondendo."""
    async def run_checks() -> dict[str, bool]:
        database_ok, redis_ok = await asyncio.gather(
            _check("database", _ping_database(engine)),
            _check("redis", redis.ping()),
        )
        return {"database": database_ok, "redis": redis_ok}

    checks = await readiness_cache.get(run_checks)

    if not all(checks.values()):
        details: JsonObject = {"checks": {name: ok for name, ok in checks.items()}}
        raise ServiceUnavailableError(message="Service dependencies are not ready.", details=details)

    return ApiResponse.success(ReadinessResponse(checks=checks))


async def _ping_database(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _check(name: str, probe: Awaitable[object]) -> bool:
    try:
        await asyncio.wait_for(probe, timeout=_CHECK_TIMEOUT_SECONDS)
        return True
    except Exception as exc:
        log.warning("readiness.check_failed", dependency=name, error=str(exc))
        return False
