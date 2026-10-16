from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

import jwt
from pydantic import BaseModel, ConfigDict, ValidationError

from src.modules.identity.domain.ports.token_service import ITokenService, TokenKind
from src.shared.domain import UnauthorizedError, UserId


class _Claims(BaseModel):
    model_config = ConfigDict(frozen=True)

    sub: UUID
    type: Literal["access", "refresh"]
    iat: int
    exp: int
    # Único por token: dois tokens emitidos no mesmo segundo seriam idênticos sem ele (a rotação
    # do refresh compara o token inteiro). Opcional só para aceitar tokens emitidos antes dele.
    jti: str | None = None


class JwtTokenService(ITokenService):
    def __init__(self, secret_key: str, algorithm: str) -> None:
        self._secret = secret_key
        self._algorithm = algorithm

    def issue(self, user_id: UserId, kind: TokenKind, ttl: timedelta) -> str:
        now = datetime.now(UTC)
        claims = _Claims(
            sub=user_id,
            type=kind.value,
            iat=int(now.timestamp()),
            exp=int((now + ttl).timestamp()),
            jti=uuid4().hex,
        )
        return jwt.encode(claims.model_dump(mode="json"), self._secret, algorithm=self._algorithm)

    def verify(self, token: str, kind: TokenKind) -> UserId:
        label = kind.value.capitalize()
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            claims = _Claims.model_validate(payload)
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError(f"{label} token expired.") from exc
        except (jwt.InvalidTokenError, ValidationError) as exc:
            raise UnauthorizedError(f"Invalid {kind.value} token.") from exc

        if claims.type != kind.value:
            raise UnauthorizedError("Invalid token type.")
        return UserId(claims.sub)
