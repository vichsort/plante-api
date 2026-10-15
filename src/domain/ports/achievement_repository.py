from abc import ABC, abstractmethod
from typing import Any


class IAchievementRepository(ABC):
    """
    Porta para gerenciar e consultar as conquistas (badges) dos usuários.
    """
    
    @abstractmethod
    async def get_user_achievements_view(self, user_id: int) -> list[dict[str, Any]]:
        """
        Retorna uma lista de dicionários com as medalhas desbloqueadas.
        Ex: [{"badge_code": "FIRST_PLANT", "unlocked_at": "..."}]
        """
        ...

    @abstractmethod
    async def grant_badge(self, user_id: int, badge_code: str) -> None:
        """Registra que o usuário ganhou uma nova conquista."""
        ...