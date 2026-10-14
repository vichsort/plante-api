import inspect
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from src.api.exception_handlers import register_exception_handlers
from src.api.middleware import (
    AuditMiddleware,
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from src.api.openapi import COMMON_ERROR_RESPONSES
from src.infrastructure.container import Container

log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
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
        "redis": container.adapters.redis().aclose,
        "weather_http": container.adapters.weather_http().aclose,
    }
    for name, close in closers.items():
        try:
            await close()
        except Exception as exc:
            log.warning("plante.shutdown_failed", resource=name, error=str(exc))


def create_app() -> FastAPI:
    container = Container()
    container.wire(modules=[
        "src.api.deps",
        "src.api.routers.auth",
        "src.api.routers.identification",
        "src.api.routers.garden",
        "src.api.routers.plants",
        "src.api.routers.health",
        "src.api.routers.profile",
        "src.api.routers.probes",
    ])

    app = FastAPI(
        title="PlantE API",
        description="Sistema de identificação e gestão botânica",
        version="0.0.0",
        lifespan=lifespan,
    )

    app.state.container = container

    # Middlewares (registrados na ordem interna -> externa)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, redis_provider=container.adapters.redis)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)

    from src.api.routers import (
        auth,
        garden,
        health,
        identification,
        plants,
        probes,
        profile,
    )
    for domain in (auth, identification, garden, plants, health, profile):
        app.include_router(domain.router, responses=COMMON_ERROR_RESPONSES)
    # Probes ficam fora do rate limit, então não documentam os erros comuns (ex.: 429)
    app.include_router(probes.router)

    return app

app = create_app()