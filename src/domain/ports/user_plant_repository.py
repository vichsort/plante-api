from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from src.domain.entities.plant_species import PlantSpecies
from src.domain.entities.user_plant import UserPlant
from src.domain.value_objects.ids import IdentificationId, UserId, UserPlantId


@dataclass(frozen=True)
class PlantDetails:
    """Planta do jardim com a espécie correspondente (None enquanto a espécie não foi cadastrada)."""
    plant: UserPlant
    species: PlantSpecies | None


class IUserPlantRepository(ABC):
    @abstractmethod
    async def save(self, user_plant: UserPlant) -> UserPlant:
        ...

    @abstractmethod
    async def get_by_id(self, user_plant_id: UserPlantId, user_id: UserId | None = None) -> UserPlant | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: UserId) -> list[UserPlant]:
        ...

    @abstractmethod
    async def delete(self, user_plant_id: UserPlantId, user_id: UserId) -> bool:
        ...

    @abstractmethod
    async def count_by_user(self, user_id: UserId) -> int:
        """Plantas ativas no jardim (as apagadas não contam para o limite do plano)."""
        ...

    @abstractmethod
    async def get_by_identification(self, identification_id: IdentificationId, user_id: UserId) -> UserPlant | None:
        """Planta ativa criada a partir da identificação, se houver."""
        ...

    @abstractmethod
    async def get_details(self, user_plant_id: UserPlantId, user_id: UserId) -> PlantDetails | None:
        ...

    @abstractmethod
    async def list_with_streak_due_before(self, due_before: date) -> list[UserPlant]:
        """Plantas com sequência em andamento e vencimento anterior a `due_before`."""
        ...
