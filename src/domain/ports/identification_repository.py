from abc import ABC, abstractmethod

from src.domain.entities.identification import Identification
from src.domain.value_objects.ids import IdentificationId, UserId


class IIdentificationRepository(ABC):
    @abstractmethod
    async def save(self, identification: Identification) -> Identification:
        ...

    @abstractmethod
    async def get_for_user(self, identification_id: IdentificationId, user_id: UserId) -> Identification | None:
        """None se não existe ou se é de outro usuário (a API não distingue os dois casos)."""
        ...
