from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog

from src.bootstrap.container import Container

log = structlog.stdlib.get_logger()


async def close_connections(container: Container) -> None:
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


@asynccontextmanager
async def task_container(container: Container | None) -> AsyncIterator[Container]:
    """
    Container de uma task do Celery. O criado aqui é fechado no fim, ainda dentro do event loop
    da task: antes o coletor de lixo fechava o Redis depois do loop (aviso "Event loop is closed").
    O recebido (testes) é de quem chamou e fica aberto.
    """
    if container is not None:
        yield container
        return
    owned = Container()
    try:
        yield owned
    finally:
        await close_connections(owned)
