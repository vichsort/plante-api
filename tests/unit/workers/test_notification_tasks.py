import uuid
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.container import Container
from src.workers.notification_tasks import send_verification_email_task


@pytest.mark.asyncio
async def test_send_verification_email_task():
    user_id = str(uuid.uuid4())
    email = "user@plante.org"

    mock_otp_repo = AsyncMock()
    mock_email_sender = AsyncMock()

    container = Container()
    with container.adapters.otp_repository.override(mock_otp_repo), container.adapters.email_sender.override(mock_email_sender):
        await send_verification_email_task(user_id, email, container=container)

    mock_otp_repo.save_code.assert_called_once()
    mock_email_sender.send_verification_code.assert_called_once()
