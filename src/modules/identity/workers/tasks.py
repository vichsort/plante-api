from uuid import UUID

import structlog
from celery import shared_task
from dependency_injector.wiring import Provide, inject
from pydantic import BaseModel, EmailStr

from src.modules.identity.container import IdentityContainer
from src.modules.identity.domain.events import UserRegisteredEvent
from src.modules.identity.domain.ports.email_sender import IEmailSender
from src.modules.identity.domain.ports.otp_repository import IOtpRepository
from src.modules.identity.domain.value_objects.verification_code import VerificationCode
from src.shared.adapters import TaskCall
from src.shared.domain import DomainEvent, UserId
from src.shared.workers import run_async

log = structlog.stdlib.get_logger()
_OTP_EXPIRES_MINUTES = 15
SEND_VERIFICATION_EMAIL_TASK = "notification.send_verification_email"


class _VerificationEmailPayload(BaseModel):
    """Argumentos da task, validados no worker: a mensagem vem da fila, de fora do processo."""
    user_id: UUID
    email: EmailStr


def route_event(event: DomainEvent) -> TaskCall | None:
    """Os eventos do identity que viram task (a composição entrega esta rota ao publisher)."""
    if isinstance(event, UserRegisteredEvent):
        return TaskCall(SEND_VERIFICATION_EMAIL_TASK, {"user_id": str(event.user_id), "email": event.email})
    return None


@shared_task(
    name=SEND_VERIFICATION_EMAIL_TASK,
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
@inject
async def send_verification_email_task(
    user_id: str,
    email: str,
    otp_repo: IOtpRepository = Provide[IdentityContainer.otp_repository],
    email_sender: IEmailSender = Provide[IdentityContainer.email_sender],
) -> None:
    """As dependências vêm do container ligado pela composição; os testes podem passá-las direto."""
    payload = _VerificationEmailPayload(user_id=UUID(user_id), email=email)
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
