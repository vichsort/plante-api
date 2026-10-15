from typing import Protocol

import structlog

from src.domain.events.domain_events import DomainEvent, UserRegisteredEvent
from src.domain.ports.domain_publisher import IDomainPublisher

log = structlog.stdlib.get_logger()

# Publicado pelo nome: o adapter não importa `src.workers` (camada acima dele). O teste do
# publisher confere que o nome é de uma task registrada.
SEND_VERIFICATION_EMAIL_TASK = "notification.send_verification_email"


class TaskSender(Protocol):
    """O que o publisher usa do app do Celery (o `Celery` dos stubs é genérico sobre `Task[Any, Any]`)."""
    def send_task(self, name: str, *, kwargs: dict[str, str]) -> object: ...


class CeleryPublisher(IDomainPublisher):
    def __init__(self, celery_app: TaskSender) -> None:
        self._celery = celery_app

    async def publish(self, event: DomainEvent) -> None:
        log.info("event.published", event_type=type(event).__name__)

        if isinstance(event, UserRegisteredEvent):
            self._celery.send_task(
                SEND_VERIFICATION_EMAIL_TASK,
                kwargs={"user_id": str(event.user_id), "email": event.email},
            )
