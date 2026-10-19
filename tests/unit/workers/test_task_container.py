import pytest

from src.bootstrap.connections import task_container
from src.bootstrap.container import Container


class _Closable:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    async def dispose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_container_created_by_the_task_is_closed_inside_its_event_loop() -> None:
    # Arrange
    redis, engine = _Closable(), _Closable()

    # Act
    async with task_container(None) as container:
        container.adapters.redis.override(redis)
        container.infra.engine.override(engine)

    # Assert: antes o Redis só fechava no coletor de lixo, com o loop da task já fechado
    assert redis.closed
    assert engine.closed


@pytest.mark.asyncio
async def test_container_created_by_the_task_is_closed_when_the_task_fails() -> None:
    # Arrange
    redis = _Closable()

    # Act & Assert
    with pytest.raises(RuntimeError):
        async with task_container(None) as container:
            container.adapters.redis.override(redis)
            container.infra.engine.override(_Closable())
            raise RuntimeError("boom")
    assert redis.closed


@pytest.mark.asyncio
async def test_container_received_by_the_task_stays_open() -> None:
    # Arrange
    received = Container()
    redis = _Closable()
    received.adapters.redis.override(redis)

    # Act
    async with task_container(received) as container:
        pass

    # Assert
    assert container is received
    assert not redis.closed
