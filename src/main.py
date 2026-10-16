import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from src.bootstrap.container import Container
from src.bootstrap.wiring import wire
from src.shared.adapters import CircuitBreaker
from src.shared.api import (
    COMMON_ERROR_RESPONSES,
    AuditMiddleware,
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    install_authentication,
    register_exception_handlers,
)

log = structlog.stdlib.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = app.state.container

    # init/shutdown_resources só retornam awaitable quando há Resources assíncronos
    if inspect.isawaitable(result := container.init_resources()):
        await result
    log.info("plante.startup")

    yield

    if inspect.isawaitable(result := container.shutdown_resources()):
        await result
    await _close_connections(container)

    log.info("plante.shutdown")


async def _close_connections(container: Container) -> None:
    """Fecha pools e clientes de rede; uma falha não impede o fechamento dos demais."""
    closers = {
        "database": container.infra.engine().dispose,
        "redis": container.adapters.redis().close,
    }
    for name, close in closers.items():
        try:
            await close()
        except Exception as exc:
            log.warning("plante.shutdown_failed", resource=name, error=str(exc))


def create_app() -> FastAPI:
    container = Container()
    wire(container)

    app = FastAPI(
        title="PlantE API",
        description="Sistema de identificação e gestão botânica",
        version="0.0.0",
        lifespan=lifespan,
    )

    app.state.container = container
    install_authentication(app, container.identity.token_service)

    # Middlewares (registrados na ordem interna -> externa)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        redis_provider=container.adapters.redis,
        token_decoder=container.identity.token_service().owner_of,
        # Após uma falha do Redis, só o contador em memória por 30s antes de tentar de novo
        redis_breaker=CircuitBreaker("Redis", failure_threshold=1, recovery_timeout_seconds=30.0),
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)

    from src.api.routers import (
        garden,
        health,
        identification,
        plants,
        profile,
    )
    from src.bootstrap import probes
    from src.modules.identity import api as identity
    from src.modules.subscription import api as subscription
    for domain in (identity, identification, garden, plants, health, profile, subscription):
        app.include_router(domain.router, responses=COMMON_ERROR_RESPONSES)
    # Probes ficam fora do rate limit, então não documentam os erros comuns (ex.: 429)
    app.include_router(probes.router)

    return app

app = create_app()