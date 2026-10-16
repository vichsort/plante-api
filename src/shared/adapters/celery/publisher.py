from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import structlog

from src.shared.domain import DomainEvent, IDomainPublisher

log = structlog.stdlib.get_logger()


@dataclass(frozen=True)
class TaskCall:
    """Uma task para a fila, pelo nome: quem publica não importa o worker (camada acima)."""
    name: str
    kwargs: dict[str, str]


# Cada módulo diz quais eventos dele viram task; `None` = o evento não é desta rota
EventRoute = Callable[[DomainEvent], TaskCall | None]


class TaskSender(Protocol):
    """O que o publisher usa do app do Celery (o `Celery` dos stubs é genérico sobre `Task[Any, Any]`)."""
    def send_task(self, name: str, *, kwargs: dict[str, str]) -> object: ...


class CeleryPublisher(IDomainPublisher):
    """
    Publica eventos de domínio como tasks do Celery. As rotas vêm dos módulos, montadas na
    composição; evento sem rota só é logado (ninguém o consome ainda).
    """

    def __init__(self, celery_app: TaskSender, routes: Sequence[EventRoute]) -> None:
        self._celery = celery_app
        self._routes = tuple(routes)

    async def publish(self, event: DomainEvent) -> None:
        log.info("event.published", event_type=type(event).__name__)

        for route in self._routes:
            call = route(event)
            if call is not None:
                self._celery.send_task(call.name, kwargs=call.kwargs)
