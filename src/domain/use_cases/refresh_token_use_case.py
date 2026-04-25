from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import jwt
import structlog

from src.domain.ports.token_repository import ITokenRepository
from src.domain.exceptions import UnauthorizedError

log = structlog.get_logger()

_ACCESS_TTL = timedelta(minutes=15)

@dataclass(frozen=True)
class RefreshResult:
    access_token: str
    token_type: str = "bearer"

class RefreshTokenUseCase:
    def __init__(
        self,
        token_repo: ITokenRepository,
        secret_key: str,
        algorithm: str = "HS256",
    ) -> None:
        self._token_repo = token_repo
        self._secret = secret_key
        self._algorithm = algorithm

    async def execute(self, refresh_token: str) -> RefreshResult:
        try:
            payload = jwt.decode(
                refresh_token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Refresh token expired.")
        except jwt.InvalidTokenError:
            raise UnauthorizedError("Invalid refresh token.")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type.")

        user_id = int(payload["sub"])

        stored = await self._token_repo.get_refresh_token(user_id)
        if stored != refresh_token:
            raise UnauthorizedError("Refresh token revoked or superseded.")

        now = datetime.now(timezone.utc)
        access_token = jwt.encode(
            {
                "sub": str(user_id),
                "type": "access",
                "iat": now,
                "exp": now + _ACCESS_TTL,
            },
            self._secret,
            algorithm=self._algorithm,
        )

        log.info("token.refreshed", user_id=user_id)
        return RefreshResult(access_token=access_token)