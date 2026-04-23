from abc import ABC, abstractmethod
from src.domain.entities.user_plant import UserPlant

class IUserPlantRepository(ABC):
    @abstractmethod
    async def save(self, user_plant: UserPlant) -> UserPlant:
        ...

    @abstractmethod
    async def get_by_id(self, user_plant_id: int, user_id: int) -> UserPlant | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[UserPlant]:
        ...

    @abstractmethod
    async def delete(self, user_plant_id: int, user_id: int) -> bool:
        ...

    @abstractmethod
    async def count_by_user(self, user_id: int) -> int:
        """Necessário pra verificar limite do plano Free antes de adicionar."""
        ...