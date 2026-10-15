from dataclasses import dataclass

from src.domain.exceptions import PlantNotFoundError
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.ports.user_plant_repository import PlantDetails
from src.domain.value_objects.ids import UserId, UserPlantId


@dataclass(frozen=True)
class GetPlantDetailsInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId

class GetPlantDetailsUseCase:
    raises = (PlantNotFoundError,)

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: GetPlantDetailsInputDTO) -> PlantDetails:
        async with self.uow as uow:
            details = await uow.user_plants.get_details(dto.user_plant_id, dto.user_id)

        if details is None:
            raise PlantNotFoundError(dto.user_plant_id)

        return details
