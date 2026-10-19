from dataclasses import dataclass

from src.modules.garden import IPlantLookup, PlantNotFoundError, UserPlantId
from src.modules.health.domain.entities.health_record import HealthRecord
from src.modules.health.domain.ports.unit_of_work import IHealthUnitOfWork
from src.shared.domain import UserId


@dataclass(frozen=True)
class GetHealthHistoryInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    limit: int = 20

class GetHealthHistoryUseCase:
    raises = (PlantNotFoundError,)

    def __init__(self, uow: IHealthUnitOfWork, plants: IPlantLookup) -> None:
        self._uow = uow
        self._plants = plants

    async def execute(self, dto: GetHealthHistoryInputDTO) -> list[HealthRecord]:
        async with self._uow as uow:
            await self._plants.get_for_user(dto.user_plant_id, dto.user_id)

            return await uow.health_records.list_by_plant(
                user_plant_id=dto.user_plant_id,
                limit=dto.limit,
            )
