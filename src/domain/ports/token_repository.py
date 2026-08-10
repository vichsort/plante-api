from abc import ABC, abstractmethod
from typing import Any


class ITokenRepository(ABC):
    @abstractmethod
    async def save_refresh_token(
        self,
        user_id: Any,
        token: str,
        ttl_seconds: int,
    ) -> None:
        """Persiste o refresh token, sobrescrevendo qualquer sessão anterior."""
        ...

    @abstractmethod
    async def get_refresh_token(self, user_id: Any) -> str | None:
        """Retorna o refresh token ativo do usuário, ou None se inexistente/expirado."""
        ...

    @abstractmethod
    async def delete_refresh_token(self, user_id: Any) -> None:
        """Remove o refresh token — usado no logout."""
        ...