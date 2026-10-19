from dataclasses import dataclass
from datetime import timedelta

import structlog

from src.modules.identity.domain.exceptions import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
)
from src.modules.identity.domain.ports.password_hasher import IPasswordHasher
from src.modules.identity.domain.ports.token_repository import ITokenRepository
from src.modules.identity.domain.ports.token_service import ITokenService, TokenKind
from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.modules.identity.domain.value_objects.email import normalize_email

log = structlog.stdlib.get_logger()

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginUseCase:
    # Not 401: that one only means "renew the token or sign in again"
    raises = (EmailNotVerifiedError, InvalidCredentialsError)

    def __init__(
        self,
        uow: IIdentityUnitOfWork,
        hasher: IPasswordHasher,
        token_repo: ITokenRepository,
        token_service: ITokenService,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._token_repo = token_repo
        self._token_service = token_service

    async def execute(self, email: str, password: str) -> LoginResult:
        async with self._uow as uow:
            user = await uow.users.get_by_email(normalize_email(email))

        if not user or not self._hasher.verify(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_verified:
            raise EmailNotVerifiedError()

        access_token = self._token_service.issue(user.id, TokenKind.ACCESS, ACCESS_TOKEN_TTL)
        refresh_token = self._token_service.issue(user.id, TokenKind.REFRESH, REFRESH_TOKEN_TTL)

        await self._token_repo.save_refresh_token(
            user_id=user.id,
            token=refresh_token,
            ttl_seconds=int(REFRESH_TOKEN_TTL.total_seconds()),
        )

        log.info("user.login", user_id=str(user.id))
        return LoginResult(access_token=access_token, refresh_token=refresh_token)
