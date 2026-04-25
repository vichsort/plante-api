from contextlib import asynccontextmanager
import structlog

from fastapi import FastAPI
from src.infrastructure.container import Container
from src.api.exception_handlers import register_exception_handlers

log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    container = app.state.container

    await container.init_resources()
    log.info("plante.startup")

    yield

    await container.shutdown_resources()
    await container.weather_http().aclose()
    log.info("plante.shutdown")


def create_app() -> FastAPI:
    container = Container()
    container.wire(modules=[
        "src.api.deps",
        "src.api.routers.auth",
        "src.api.routers.garden",
        "src.api.routers.plants",
        "src.api.routers.profile",
    ])

    app = FastAPI(
        title="PlantE API",
        description="Sistema de identificação e gestão botânica",
        version="0.0.0",
        lifespan=lifespan,
    )

    app.state.container = container

    register_exception_handlers(app)

    from src.api.routers import auth, garden, plants, profile
    app.include_router(auth.router)
    app.include_router(garden.router)
    app.include_router(plants.router)
    app.include_router(profile.router)

    @app.get("/health", tags=["infra"])
    async def health_check():
        return {"status": "ok", "service": "plante-api"}

    return app

app = create_app()