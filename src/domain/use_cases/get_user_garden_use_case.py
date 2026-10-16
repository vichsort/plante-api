from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.user_plant import GardenPlant
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import UserId
from src.domain.value_objects.local_calendar import LocalCalendar


@dataclass(frozen=True)
class GetUserGardenInputDTO:
    user_id: UserId

class GetUserGardenUseCase:
    raises = ()

    def __init__(self, uow: IUnitOfWork, calendar: LocalCalendar) -> None:
        self.uow = uow
        self.calendar = calendar

    async def execute(self, dto: GetUserGardenInputDTO) -> list[GardenPlant]:
        async with self.uow as uow:
            plants = await uow.user_plants.list_by_user(dto.user_id)

        today = self.calendar.date_of(datetime.now(UTC))
        return [GardenPlant.of(plant, today) for plant in plants]
