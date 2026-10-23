from datetime import UTC, datetime
from uuid import uuid4

from src.modules.identity.domain.events import UserRegisteredEvent
from src.modules.identity.tests.fakes import InMemoryOtpRepository, RecordingEmailSender
from src.modules.identity.workers.tasks import (
    SEND_VERIFICATION_EMAIL_TASK,
    route_event,
    send_verification_email_task,
)
from src.shared.adapters import TaskCall
from src.shared.domain import DomainEvent, UserId


async def test_task_saves_a_new_code_and_emails_it() -> None:
    # Arrange
    user_id = UserId(uuid4())
    otp, sender = InMemoryOtpRepository(), RecordingEmailSender()

    # Act
    await send_verification_email_task(str(user_id), "user@plante.org", otp_repo=otp, email_sender=sender)

    # Assert
    assert sender.sent == [("user@plante.org", otp.codes[user_id])]


async def test_retry_reuses_the_active_code_instead_of_generating_a_new_one() -> None:
    # Arrange: a mesma task entregue de novo; o e-mail que chegar tem de ter o código aceito
    user_id = UserId(uuid4())
    otp, sender = InMemoryOtpRepository(), RecordingEmailSender()
    otp.codes[user_id] = "PLA1234567"

    # Act
    await send_verification_email_task(str(user_id), "user@plante.org", otp_repo=otp, email_sender=sender)

    # Assert
    assert sender.sent == [("user@plante.org", "PLA1234567")]


def test_task_is_acknowledged_only_after_running() -> None:
    # Act & Assert: worker encerrado no meio devolve a task para a fila (antes ela se perdia)
    assert (send_verification_email_task.acks_late, send_verification_email_task.reject_on_worker_lost) == (True, True)


def test_registration_is_routed_to_the_verification_email() -> None:
    # Arrange
    user_id = UserId(uuid4())

    # Act
    call = route_event(UserRegisteredEvent.create(user_id=user_id, email="new@plante.org", requires_verification=True))

    # Assert
    assert call == TaskCall(SEND_VERIFICATION_EMAIL_TASK, {"user_id": str(user_id), "email": "new@plante.org"})


def test_registration_without_verification_sends_no_email() -> None:
    # Act
    call = route_event(UserRegisteredEvent.create(user_id=UserId(uuid4()), email="new@plante.org", requires_verification=False))

    # Assert
    assert call is None


def test_other_events_are_not_routed() -> None:
    # Act
    call = route_event(DomainEvent(occurred_on=datetime.now(UTC)))

    # Assert
    assert call is None
