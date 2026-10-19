from uuid import UUID

import structlog
from pydantic import BaseModel, EmailStr

from src.bootstrap.celery_config import celery_app
from src.bootstrap.connections import task_container
from src.bootstrap.container import Container
from src.domain.value_objects.verification_code import VerificationCode
from src.shared.domain import UserId
from src.shared.workers import run_async

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
    # Confirma a mensagem só no fim: worker encerrado no meio (deploy, queda) devolve a task
    # para a fila em vez de perdê-la
    acks_late=True,
    reject_on_worker_lost=True,
)
@run_async
async def send_verification_email_task(user_id: str, email: str, container: Container | None = None) -> None:
    payload = _VerificationEmailPayload(user_id=UUID(user_id), email=email)
    async with task_container(container) as cnt:
        otp_repo = cnt.adapters.otp_repository()
        email_sender = cnt.adapters.email_sender()

        user_id_typed = UserId(payload.user_id)
        # Nova tentativa (ou a mesma task entregue de novo) reaproveita o código ainda válido: o
        # e-mail que chegar tem sempre o código aceito
        raw_code = await otp_repo.get_active_code_for_user(user_id_typed)
        if raw_code is None:
            raw_code = VerificationCode.generate().raw_code
            await otp_repo.save_code(
                user_id=user_id_typed,
                code=raw_code,
                expires_in_minutes=_OTP_EXPIRES_MINUTES,
            )

        await email_sender.send_verification_code(
            to_email=payload.email,
            code=raw_code,
        )

    log.info("email.verification_sent", user_id=user_id)