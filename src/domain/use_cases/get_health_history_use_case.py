from dataclasses import dataclass

from src.domain.entities.health_record import HealthRecord
from src.domain.exceptions import PlantNotFoundError
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import UserId, UserPlantId


@dataclass(frozen=True)
class GetHealthHistoryInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    limit: int = 20

class GetHealthHistoryUseCase:
    raises = (PlantNotFoundError,)

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, dto: GetHealthHistoryInputDTO) -> list[HealthRecord]:
        async with self._uow as uow:
            user_plant = await uow.user_plants.get_by_id(dto.user_plant_id, dto.user_id)
            if not user_plant:
                raise PlantNotFoundError(dto.user_plant_id)

            return await uow.health_records.list_by_plant(
                user_plant_id=dto.user_plant_id,
                limit=dto.limit,
            )
