from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.identity.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from src.modules.identity.adapters.redis.otp_repository import RedisOtpRepository
from src.modules.identity.adapters.redis.token_repository import RedisTokenRepository
from src.modules.identity.adapters.security.bcrypt_hasher import BcryptHasher
from src.modules.identity.adapters.security.jwt_token_service import JwtTokenService
from src.modules.identity.adapters.ses.email_sender import SesEmailSender
from src.modules.identity.domain.services.user_directory import UserDirectory
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
from src.shared.adapters import RedisClient
from src.shared.domain import IDomainPublisher, IImageStorage


class IdentityContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    redis: providers.Dependency[RedisClient] = providers.Dependency()
    publisher: providers.Dependency[IDomainPublisher] = providers.Dependency()
    storage: providers.Dependency[IImageStorage] = providers.Dependency()
    secret_key: providers.Dependency[str] = providers.Dependency()
    jwt_algorithm: providers.Dependency[str] = providers.Dependency()
    aws_region: providers.Dependency[str] = providers.Dependency()
    ses_sender_email: providers.Dependency[str] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyIdentityUnitOfWork, session_factory=session_factory)
    directory = providers.Factory(UserDirectory, uow=unit_of_work)

    password_hasher = providers.Singleton(BcryptHasher)
    token_service = providers.Singleton(JwtTokenService, secret_key=secret_key, algorithm=jwt_algorithm)
    token_repository = providers.Singleton(RedisTokenRepository, redis=redis)
    otp_repository = providers.Singleton(RedisOtpRepository, redis=redis)
    email_sender = providers.Singleton(SesEmailSender, region=aws_region, sender_email=ses_sender_email)

    register_user_use_case = providers.Factory(
        RegisterUserUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        publisher=publisher,
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
    )
    change_password_use_case = providers.Factory(
        ChangePasswordUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        email_sender=email_sender,
    )
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
