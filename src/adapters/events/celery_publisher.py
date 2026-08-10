import structlog

from src.domain.events.domain_events import DomainEvent, UserRegisteredEvent
from src.domain.ports.domain_publisher import IDomainPublisher

log = structlog.get_logger()


class CeleryPublisher(IDomainPublisher):
    async def publish(self, event: DomainEvent) -> None:
        log.info("event.published", event_type=type(event).__name__)

        if isinstance(event, UserRegisteredEvent):
            from src.workers.notification_tasks import send_verification_email_task
            send_verification_email_task.delay(
                user_id=event.user_id,
                email=event.email,
            )