from dataclasses import dataclass
from datetime import timedelta

import structlog

from src.domain.exceptions import UnauthorizedError
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.token_repository import ITokenRepository
from src.domain.ports.token_service import ITokenService, TokenKind
from src.domain.ports.user_repository import IUserRepository

log = structlog.stdlib.get_logger()

ACCESS_TOKEN_TTL = timedelta(minutes=15)
_REFRESH_TTL = timedelta(days=30)


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginUseCase:
    raises = (UnauthorizedError,)

    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: IPasswordHasher,
        token_repo: ITokenRepository,
        token_service: ITokenService,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher
        self._token_repo = token_repo
        self._token_service = token_service

    async def execute(self, email: str, password: str) -> LoginResult:
        user = await self._user_repo.get_by_email(email)
        if not user or not self._hasher.verify(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_verified:
            raise UnauthorizedError("Email not verified.")

        access_token = self._token_service.issue(user.id, TokenKind.ACCESS, ACCESS_TOKEN_TTL)
        refresh_token = self._token_service.issue(user.id, TokenKind.REFRESH, _REFRESH_TTL)

        await self._token_repo.save_refresh_token(
            user_id=user.id,
            token=refresh_token,
            ttl_seconds=int(_REFRESH_TTL.total_seconds()),
        )

        log.info("user.login", user_id=str(user.id))
        return LoginResult(access_token=access_token, refresh_token=refresh_token)
