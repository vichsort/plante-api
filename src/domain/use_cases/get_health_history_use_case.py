from dataclasses import dataclass

from src.domain.entities.health_record import HealthRecord
from src.domain.exceptions import PlantNotFoundError
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.value_objects.ids import UserId, UserPlantId


@dataclass(frozen=True)
class GetHealthHistoryInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    limit: int = 20

class GetHealthHistoryUseCase:
    raises = (PlantNotFoundError,)

    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        health_repo: IHealthRecordRepository,
    ) -> None:
        self._user_plant_repo = user_plant_repo
        self._health_repo = health_repo

    async def execute(self, dto: GetHealthHistoryInputDTO) -> list[HealthRecord]:
        user_plant = await self._user_plant_repo.get_by_id(dto.user_plant_id, dto.user_id)
        if not user_plant:
            raise PlantNotFoundError(dto.user_plant_id)

        return await self._health_repo.list_by_plant(
            user_plant_id=dto.user_plant_id,
            limit=dto.limit,
        )
