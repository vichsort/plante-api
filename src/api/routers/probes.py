import asyncio
from collections.abc import Awaitable

import structlog
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.response import ApiResponse
from src.infrastructure.container import Container

log = structlog.get_logger()

_CHECK_TIMEOUT_SECONDS = 2.0

router = APIRouter(prefix="/health", tags=["infra"])


@router.get("/liveness", status_code=200, response_model=ApiResponse[dict])
async def liveness():
    """Processo está de pé. Não verifica dependências externas."""
    return ApiResponse.success(data={"status": "alive"})


@router.get(
    "/readiness",
    status_code=200,
    response_model=ApiResponse[dict],
    responses={503: {"model": ApiResponse[None], "description": "PLANTE_5003_SERVICE_NOT_READY"}},
)
@inject
async def readiness(
    engine: AsyncEngine = Depends(Provide[Container.infra.engine]),
    redis: Redis = Depends(Provide[Container.adapters.redis]),
):
    """Instância pronta para receber tráfego: Postgres e Redis respondendo."""
    database_ok, redis_ok = await asyncio.gather(
        _check("database", _ping_database(engine)),
        _check("redis", redis.ping()),
    )
    checks = {"database": database_ok, "redis": redis_ok}

    if not all(checks.values()):
        body = ApiResponse.fail(
            code="PLANTE_5003_SERVICE_NOT_READY",
            message="Service dependencies are not ready.",
            details={"checks": checks},
        )
        return JSONResponse(status_code=503, content=body.model_dump())

    return ApiResponse.success(data={"status": "ready", "checks": checks})


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
