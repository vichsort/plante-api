import uuid
from unittest.mock import MagicMock

from celery import Celery

import src.workers.notification_tasks  # noqa: F401  (registra as tasks no celery_app)
from src.adapters.events.celery_publisher import (
    SEND_VERIFICATION_EMAIL_TASK,
    CeleryPublisher,
)
from src.domain.events.domain_events import UserRegisteredEvent
from src.domain.value_objects.ids import UserId
from src.infrastructure.celery_config import celery_app


def test_verification_task_name_is_registered() -> None:
    # O publisher publica pelo nome, sem importar o worker: o nome tem de existir
    assert SEND_VERIFICATION_EMAIL_TASK in celery_app.tasks


async def test_user_registered_sends_verification_task() -> None:
    app = MagicMock(spec=Celery)
    user_id = UserId(uuid.uuid4())

    await CeleryPublisher(app).publish(UserRegisteredEvent.create(user_id=user_id, email="new@plante.org"))

    app.send_task.assert_called_once_with(
        SEND_VERIFICATION_EMAIL_TASK,
        kwargs={"user_id": str(user_id), "email": "new@plante.org"},
    )
