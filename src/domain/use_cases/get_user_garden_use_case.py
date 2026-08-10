from dataclasses import dataclass
from typing import Any

from src.domain.ports.user_plant_repository import IUserPlantRepository


@dataclass(frozen=True)
class GetUserGardenInputDTO:
    user_id: Any

class GetUserGardenUseCase:
    def __init__(self, user_plant_repo: IUserPlantRepository):
        self.user_plant_repo = user_plant_repo

    async def execute(self, dto: GetUserGardenInputDTO) -> list[dict]:
        return await self.user_plant_repo.get_garden_view_for_user(dto.user_id)