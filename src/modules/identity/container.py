from collections.abc import Callable
from typing import Literal

import structlog
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.identity.adapters.captcha.turnstile import (
    DisabledCaptchaVerifier,
    TurnstileCaptchaVerifier,
)
from src.modules.identity.adapters.email.log import LogEmailSender
from src.modules.identity.adapters.email.ses import SesEmailSender
from src.modules.identity.adapters.email.smtp import SmtpEmailSender, SmtpSecurity
from src.modules.identity.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from src.modules.identity.adapters.redis.otp_repository import RedisOtpRepository
from src.modules.identity.adapters.redis.token_repository import RedisTokenRepository
from src.modules.identity.adapters.security.bcrypt_hasher import BcryptHasher
from src.modules.identity.adapters.security.jwt_token_service import JwtTokenService
from src.modules.identity.domain.ports.captcha_verifier import ICaptchaVerifier
from src.modules.identity.domain.ports.email_sender import IEmailSender
from src.modules.identity.domain.services.user_directory import UserDirectory
from src.modules.identity.domain.use_cases.accept_terms import AcceptTermsUseCase
from src.modules.identity.domain.use_cases.change_email import ChangeEmailUseCase
from src.modules.identity.domain.use_cases.change_password import ChangePasswordUseCase
from src.modules.identity.domain.use_cases.delete_account import DeleteAccountUseCase
from src.modules.identity.domain.use_cases.login import LoginUseCase
from src.modules.identity.domain.use_cases.logout import LogoutUseCase
from src.modules.identity.domain.use_cases.refresh_token import RefreshTokenUseCase
from src.modules.identity.domain.use_cases.register_user import RegisterUserUseCase
from src.modules.identity.domain.use_cases.update_location import (
    UpdateLocationFallbackUseCase,
)
from src.modules.identity.domain.use_cases.verify_email import VerifyEmailUseCase
from src.modules.identity.domain.value_objects.terms import Terms
from src.shared.adapters import RedisClient
from src.shared.domain import IDomainPublisher, IImageStorage

log = structlog.stdlib.get_logger()

EmailBackend = Literal["log", "smtp", "ses"]


def _pick_email_sender(
    backend: EmailBackend,
    log: Callable[[], IEmailSender],
    smtp: Callable[[], IEmailSender],
    ses: Callable[[], IEmailSender],
) -> IEmailSender:
    """`EMAIL_BACKEND`: builds only the chosen sender (SES opens an AWS client)."""
    return {"log": log, "smtp": smtp, "ses": ses}[backend]()


def _captcha_verifier(secret_key: str) -> ICaptchaVerifier:
    """`TURNSTILE_SECRET_KEY`: without it the captcha is off, and the log says so (on first use)."""
    if not secret_key:
        log.warning("captcha.disabled", reason="TURNSTILE_SECRET_KEY is empty: /auth/register accepts any token")
        return DisabledCaptchaVerifier()
    return TurnstileCaptchaVerifier(secret_key)


class IdentityContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    redis: providers.Dependency[RedisClient] = providers.Dependency()
    publisher: providers.Dependency[IDomainPublisher] = providers.Dependency()
    storage: providers.Dependency[IImageStorage] = providers.Dependency()
    secret_key: providers.Dependency[str] = providers.Dependency()
    jwt_algorithm: providers.Dependency[str] = providers.Dependency()
    aws_region: providers.Dependency[str] = providers.Dependency()
    email_backend: providers.Dependency[EmailBackend] = providers.Dependency()
    email_from: providers.Dependency[str] = providers.Dependency()
    email_verification_required: providers.Dependency[bool] = providers.Dependency()
    smtp_host: providers.Dependency[str] = providers.Dependency()
    smtp_port: providers.Dependency[int] = providers.Dependency()
    smtp_username: providers.Dependency[str] = providers.Dependency()
    smtp_password: providers.Dependency[str] = providers.Dependency()
    smtp_security: providers.Dependency[SmtpSecurity] = providers.Dependency()
    turnstile_secret_key: providers.Dependency[str] = providers.Dependency()
    terms_version: providers.Dependency[str] = providers.Dependency()
    terms_url: providers.Dependency[str | None] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyIdentityUnitOfWork, session_factory=session_factory)
    terms = providers.Singleton(Terms, version=terms_version, url=terms_url)
    directory = providers.Factory(UserDirectory, uow=unit_of_work, terms=terms)

    password_hasher = providers.Singleton(BcryptHasher)
    token_service = providers.Singleton(JwtTokenService, secret_key=secret_key, algorithm=jwt_algorithm)
    token_repository = providers.Singleton(RedisTokenRepository, redis=redis)
    otp_repository = providers.Singleton(RedisOtpRepository, redis=redis)
    log_email_sender = providers.Singleton(LogEmailSender)
    smtp_email_sender = providers.Singleton(
        SmtpEmailSender,
        host=smtp_host,
        port=smtp_port,
        username=smtp_username,
        password=smtp_password,
        sender_email=email_from,
        security=smtp_security,
    )
    ses_email_sender = providers.Singleton(SesEmailSender, region=aws_region, sender_email=email_from)
    captcha_verifier = providers.Singleton(_captcha_verifier, secret_key=turnstile_secret_key)
    email_sender = providers.Singleton(
        _pick_email_sender,
        backend=email_backend,
        log=log_email_sender.provider,
        smtp=smtp_email_sender.provider,
        ses=ses_email_sender.provider,
    )

    register_user_use_case = providers.Factory(
        RegisterUserUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        publisher=publisher,
        captcha=captcha_verifier,
        terms=terms,
        verification_required=email_verification_required,
    )
    verify_email_use_case = providers.Factory(
        VerifyEmailUseCase,
        uow=unit_of_work,
        otp_repo=otp_repository,
    )
    login_use_case = providers.Factory(
        LoginUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        token_repo=token_repository,
        token_service=token_service,
        verification_required=email_verification_required,
    )
    refresh_token_use_case = providers.Factory(
        RefreshTokenUseCase,
        token_repo=token_repository,
        token_service=token_service,
    )
    logout_use_case = providers.Factory(
        LogoutUseCase,
        token_repo=token_repository,
    )
    change_email_use_case = providers.Factory(
        ChangeEmailUseCase,
        uow=unit_of_work,
        otp_repo=otp_repository,
        hasher=password_hasher,
        email_sender=email_sender,
        verification_required=email_verification_required,
    )
    change_password_use_case = providers.Factory(
        ChangePasswordUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        email_sender=email_sender,
    )
    accept_terms_use_case = providers.Factory(AcceptTermsUseCase, uow=unit_of_work, terms=terms)
    update_location_use_case = providers.Factory(
        UpdateLocationFallbackUseCase,
        uow=unit_of_work,
    )
    delete_account_use_case = providers.Factory(
        DeleteAccountUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        token_repo=token_repository,
        storage=storage,
    )
