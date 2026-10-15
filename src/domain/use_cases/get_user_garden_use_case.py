from dataclasses import dataclass

from src.domain.entities.user_plant import UserPlant
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.value_objects.ids import UserId


@dataclass(frozen=True)
class GetUserGardenInputDTO:
    user_id: UserId

class GetUserGardenUseCase:
    raises = ()

    def __init__(self, user_plant_repo: IUserPlantRepository) -> None:
        self.user_plant_repo = user_plant_repo

    async def execute(self, dto: GetUserGardenInputDTO) -> list[UserPlant]:
        return await self.user_plant_repo.list_by_user(dto.user_id)