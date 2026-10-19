import structlog

from src.bootstrap.container import Container

log = structlog.stdlib.get_logger()


async def close_connections(container: Container) -> None:
    """
    Fecha pools e clientes de rede; uma falha não impede o fechamento dos demais. O app chama no
    fim do lifespan; o worker, no fim de cada task, ainda dentro do event loop dela (`worker.py`).
    """
    closers = {
        "database": container.infra.engine().dispose,
        "redis": container.adapters.redis().close,
    }
    for name, close in closers.items():
        try:
            await close()
        except Exception as exc:
            log.warning("plante.shutdown_failed", resource=name, error=str(exc))
