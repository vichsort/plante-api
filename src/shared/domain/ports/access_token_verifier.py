from abc import ABC, abstractmethod

from src.shared.domain.exceptions import UnauthorizedError
from src.shared.domain.value_objects.ids import UserId


class IAccessTokenVerifier(ABC):
    """
    Quem é o dono de um access token. A borda HTTP (autenticação das rotas e rate limit) usa esta
    porta; o módulo que emite os tokens a implementa, e a composição liga os dois.
    """

    @abstractmethod
    def verify_access(self, token: str) -> UserId:
        """Lança `UnauthorizedError` se o token for inválido, estiver expirado ou não for de acesso."""
        ...

    def owner_of(self, token: str) -> UserId | None:
        """O dono do token, ou `None` se ele não vale (o rate limit conta esses pelo IP)."""
        try:
            return self.verify_access(token)
        except UnauthorizedError:
            return None
