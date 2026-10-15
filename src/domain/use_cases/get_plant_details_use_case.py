from dataclasses import dataclass

from src.domain.exceptions import PlantNotFoundError
from src.domain.ports.user_plant_repository import IUserPlantRepository, PlantDetails
from src.domain.value_objects.ids import UserId, UserPlantId


@dataclass(frozen=True)
class GetPlantDetailsInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId

class GetPlantDetailsUseCase:
    raises = (PlantNotFoundError,)

    def __init__(self, user_plant_repo: IUserPlantRepository) -> None:
        self.user_plant_repo = user_plant_repo

    async def execute(self, dto: GetPlantDetailsInputDTO) -> PlantDetails:
        details = await self.user_plant_repo.get_details(dto.user_plant_id, dto.user_id)
        
        if details is None:
            raise PlantNotFoundError(dto.user_plant_id)
            
        return details