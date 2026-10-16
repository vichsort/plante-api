import uuid
from unittest.mock import AsyncMock

import pytest

from src.bootstrap.container import Container
from src.workers.notification_tasks import send_verification_email_task


@pytest.mark.asyncio
async def test_send_verification_email_task():
    user_id = str(uuid.uuid4())
    email = "user@plante.org"

    mock_otp_repo = AsyncMock()
    mock_otp_repo.get_active_code_for_user.return_value = None
    mock_email_sender = AsyncMock()

    container = Container()
    with container.adapters.otp_repository.override(mock_otp_repo), container.adapters.email_sender.override(mock_email_sender):
        await send_verification_email_task(user_id, email, container=container)

    mock_otp_repo.save_code.assert_called_once()
    mock_email_sender.send_verification_code.assert_called_once()


@pytest.mark.asyncio
async def test_retry_reuses_active_code_instead_of_generating_a_new_one():
    mock_otp_repo = AsyncMock()
    mock_otp_repo.get_active_code_for_user.return_value = "PLA1234567"
    mock_email_sender = AsyncMock()

    container = Container()
    with container.adapters.otp_repository.override(mock_otp_repo), container.adapters.email_sender.override(mock_email_sender):
        await send_verification_email_task(str(uuid.uuid4()), "user@plante.org", container=container)

    mock_otp_repo.save_code.assert_not_called()
    assert mock_email_sender.send_verification_code.call_args.kwargs["code"] == "PLA1234567"


def test_task_is_acknowledged_only_after_running():
    # Worker encerrado no meio devolve a task para a fila (antes ela se perdia)
    assert send_verification_email_task.acks_late is True
    assert send_verification_email_task.reject_on_worker_lost is True
