from dataclasses import dataclass

from src.modules.garden import IPlantLookup, PlantNotFoundError, UserPlantId
from src.modules.health.domain.entities.health_record import HealthRecord
from src.modules.health.domain.ports.unit_of_work import IHealthUnitOfWork
from src.shared.domain import IImageStorage, UserId


@dataclass(frozen=True)
class GetHealthHistoryInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    limit: int = 20


@dataclass(frozen=True)
class HealthHistoryItem:
    record: HealthRecord
    image_url: str  # signed link of the photo (expires)


class GetHealthHistoryUseCase:
    raises = (PlantNotFoundError,)

    def __init__(self, uow: IHealthUnitOfWork, plants: IPlantLookup, storage: IImageStorage) -> None:
        self._uow = uow
        self._plants = plants
        self._storage = storage

    async def execute(self, dto: GetHealthHistoryInputDTO) -> list[HealthHistoryItem]:
        async with self._uow as uow:
            await self._plants.get_for_user(dto.user_plant_id, dto.user_id)

            records = await uow.health_records.list_by_plant(
                user_plant_id=dto.user_plant_id,
                limit=dto.limit,
            )

        return [HealthHistoryItem(record, await self._storage.signed_url(record.image_key)) for record in records]
