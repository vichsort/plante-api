from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.domain.entities.user_plant import UserPlant


class IUserPlantRepository(ABC):
    @abstractmethod
    async def save(self, user_plant: UserPlant) -> UserPlant:
        ...

    @abstractmethod
    async def get_by_id(self, user_plant_id: Any, user_id: Any | None = None) -> UserPlant | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: Any) -> list[UserPlant]:
        ...

    @abstractmethod
    async def delete(self, user_plant_id: Any, user_id: Any) -> bool:
        ...

    @abstractmethod
    async def count_by_user(self, user_id: Any) -> int:
        ...

    @abstractmethod
    async def get_garden_view_for_user(self, user_id: Any) -> list[dict]:
        ...

    @abstractmethod
    async def get_plant_details_view(self, user_plant_id: Any, user_id: Any) -> dict | None:
        ...

    @abstractmethod
    async def get_overdue_plants(self, current_time: datetime) -> list[UserPlant]:
        ...