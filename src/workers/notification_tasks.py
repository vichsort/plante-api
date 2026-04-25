import structlog
from src.infrastructure.celery_config import celery_app
from src.infrastructure.container import Container
from src.domain.value_objects.verification_code import VerificationCode

log = structlog.get_logger()

_OTP_EXPIRES_MINUTES = 15

@celery_app.task(
    name="notification.send_verification_email",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
async def send_verification_email_task(self, user_id: int, email: str) -> None:
    container = Container()

    otp_repo = container.otp_repository()
    email_sender = container.email_sender()

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

    log.info("email.verification_sent", user_id=user_id)