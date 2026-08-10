from typing import Any

import structlog

from src.domain.value_objects.verification_code import VerificationCode
from src.infrastructure.celery_config import celery_app
from src.infrastructure.container import Container
from src.workers.async_runner import run_async

log = structlog.get_logger()
_OTP_EXPIRES_MINUTES = 15

@celery_app.task(
    name="notification.send_verification_email",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
@run_async
async def send_verification_email_task(user_id: Any, email: str, container: Container | None = None) -> None:
    cnt = container or Container()

    otp_repo = cnt.adapters.otp_repository()
    email_sender = cnt.adapters.email_sender()

    code = VerificationCode.generate()

    await otp_repo.save_code(
        user_id=user_id,
        code=code.raw_code,
        expires_in_minutes=_OTP_EXPIRES_MINUTES,
    )

    await email_sender.send_verification_code(
        to_email=email,
        code=code.raw_code,
    )

    log.info("email.verification_sent", user_id=str(user_id))