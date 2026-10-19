from abc import ABC, abstractmethod

from src.modules.garden.domain.entities.user_plant import UserPlant
from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.shared.domain import UserId


class IPlantLookup(ABC):
    """Uma planta do jardim do usuário (o health diagnostica e lista o histórico dela). Lê dentro da transação de quem chama, se houver."""

    @abstractmethod
    async def get_for_user(self, user_plant_id: UserPlantId, user_id: UserId) -> UserPlant:
        """Lança `PlantNotFoundError` se não existe, foi tirada do jardim ou é de outro usuário."""
        ...


class PlantLookup(IPlantLookup):
    def __init__(self, uow: IGardenUnitOfWork) -> None:
        self.uow = uow

    async def get_for_user(self, user_plant_id: UserPlantId, user_id: UserId) -> UserPlant:
        async with self.uow as uow:
            plant = await uow.user_plants.get_by_id(user_plant_id, user_id)
        if plant is None:
            raise PlantNotFoundError(user_plant_id)
        return plant
