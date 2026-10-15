from uuid import UUID

import structlog
from pydantic import BaseModel, EmailStr

from src.domain.value_objects.ids import UserId
from src.domain.value_objects.verification_code import VerificationCode
from src.infrastructure.celery_config import celery_app
from src.infrastructure.container import Container
from src.workers.async_runner import run_async

log = structlog.stdlib.get_logger()
_OTP_EXPIRES_MINUTES = 15

class _VerificationEmailPayload(BaseModel):
    """Argumentos da task, validados no worker: a mensagem vem da fila, de fora do processo."""
    user_id: UUID
    email: EmailStr


@celery_app.task(
    name="notification.send_verification_email",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
@run_async
async def send_verification_email_task(user_id: str, email: str, container: Container | None = None) -> None:
    payload = _VerificationEmailPayload(user_id=UUID(user_id), email=email)
    cnt = container or Container()

    otp_repo = cnt.adapters.otp_repository()
    email_sender = cnt.adapters.email_sender()

    code = VerificationCode.generate()

    await otp_repo.save_code(
        user_id=UserId(payload.user_id),
        code=code.raw_code,
        expires_in_minutes=_OTP_EXPIRES_MINUTES,
    )

    await email_sender.send_verification_code(
        to_email=payload.email,
        code=code.raw_code,
    )

    log.info("email.verification_sent", user_id=user_id)