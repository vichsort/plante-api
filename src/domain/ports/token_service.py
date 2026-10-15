from abc import ABC, abstractmethod
from datetime import timedelta
from enum import StrEnum

from src.domain.value_objects.ids import UserId


class TokenKind(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class ITokenService(ABC):
    """Emite e valida os tokens de autenticação (access de curta duração, refresh de longa)."""

    @abstractmethod
    def issue(self, user_id: UserId, kind: TokenKind, ttl: timedelta) -> str:
        ...

    @abstractmethod
    def verify(self, token: str, kind: TokenKind) -> UserId:
        """
        Devolve o usuário dono do token.
        Lança `UnauthorizedError` se o token for inválido, estiver expirado ou for de outro tipo.
        """
        ...
