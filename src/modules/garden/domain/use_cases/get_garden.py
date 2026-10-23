from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.garden.domain.entities.user_plant import GardenPlant, UserPlant
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.shared.domain import IImageStorage, LocalCalendar, UserId


@dataclass(frozen=True)
class GetUserGardenInputDTO:
    user_id: UserId

class GetUserGardenUseCase:
    raises = ()

    def __init__(self, uow: IGardenUnitOfWork, calendar: LocalCalendar, storage: IImageStorage) -> None:
        self.uow = uow
        self.calendar = calendar
        self.storage = storage

    async def execute(self, dto: GetUserGardenInputDTO) -> list[GardenPlant]:
        async with self.uow as uow:
            plants = await uow.user_plants.list_by_user(dto.user_id)

        today = self.calendar.date_of(datetime.now(UTC))
        return [GardenPlant.of(plant, today, await self._image_url(plant)) for plant in plants]

    async def _image_url(self, plant: UserPlant) -> str | None:
        return await self.storage.signed_url(plant.primary_image_key) if plant.primary_image_key else None
