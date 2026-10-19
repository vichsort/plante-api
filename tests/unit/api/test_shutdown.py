from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bootstrap.connections import close_connections
from src.bootstrap.container import Container


@pytest.mark.asyncio
async def test_close_connections_closes_all_even_if_one_fails():
    container = Container()
    engine = MagicMock()
    engine.dispose = AsyncMock(side_effect=RuntimeError("boom"))
    redis = AsyncMock()

    with (
        container.infra.engine.override(engine),
        container.adapters.redis.override(redis),
    ):
        await close_connections(container)

    engine.dispose.assert_awaited_once()
    redis.close.assert_awaited_once()


def test_lifespan_starts_and_shuts_down():
    from fastapi.testclient import TestClient

    from src import main

    app = main.create_app()
    with TestClient(app) as client:
        assert client.get("/health/liveness").status_code == 200
