from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import jwt
import structlog

from src.domain.ports.user_repository import IUserRepository
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.token_repository import ITokenRepository
from src.domain.exceptions import UnauthorizedError

log = structlog.get_logger()

_ACCESS_TTL = timedelta(minutes=15)
_REFRESH_TTL = timedelta(days=30)
_REFRESH_TTL_SECONDS = int(_REFRESH_TTL.total_seconds())

@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: IPasswordHasher,
        token_repo: ITokenRepository,
        secret_key: str,
        algorithm: str = "HS256",
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher
        self._token_repo = token_repo
        self._secret = secret_key
        self._algorithm = algorithm

    async def execute(self, email: str, password: str) -> LoginResult:
        user = await self._user_repo.get_by_email(email)

        if not user or not self._hasher.verify(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_email_verified:
            raise UnauthorizedError("Email not verified.")

        now = datetime.now(timezone.utc)

        access_token = jwt.encode(
            {
                "sub": str(user.id),
                "type": "access",
                "iat": now,
                "exp": now + _ACCESS_TTL,
            },
            self._secret,
            algorithm=self._algorithm,
        )

        refresh_token = jwt.encode(
            {
                "sub": str(user.id),
                "type": "refresh",
                "iat": now,
                "exp": now + _REFRESH_TTL,
            },
            self._secret,
            algorithm=self._algorithm,
        )

        await self._token_repo.save_refresh_token(
            user_id=user.id,
            token=refresh_token,
            ttl_seconds=_REFRESH_TTL_SECONDS,
        )

        log.info("user.login", user_id=user.id)
        return LoginResult(access_token=access_token, refresh_token=refresh_token)