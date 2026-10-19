from abc import ABC, abstractmethod

from src.modules.identification.domain.entities.identification import Identification
from src.modules.identification.domain.exceptions import IdentificationNotFoundError
from src.modules.identification.domain.ports.unit_of_work import (
    IIdentificationUnitOfWork,
)
from src.modules.identification.domain.value_objects.ids import IdentificationId
from src.shared.domain import UserId


class IIdentificationLookup(ABC):
    """A identificação de origem de uma planta do jardim. Lê dentro da transação de quem chama, se houver."""

    @abstractmethod
    async def get_for_user(self, identification_id: IdentificationId, user_id: UserId) -> Identification:
        """Lança `IdentificationNotFoundError` se não existe ou é de outro usuário (a API não distingue)."""
        ...


class IdentificationLookup(IIdentificationLookup):
    def __init__(self, uow: IIdentificationUnitOfWork) -> None:
        self.uow = uow

    async def get_for_user(self, identification_id: IdentificationId, user_id: UserId) -> Identification:
        async with self.uow as uow:
            identification = await uow.identifications.get_for_user(identification_id, user_id)
        if identification is None:
            raise IdentificationNotFoundError(identification_id)
        return identification
