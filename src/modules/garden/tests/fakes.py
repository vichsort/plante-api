"""
Dublês do garden: `FakePlantLookup` para quem usa o módulo (o health) e, para os
testes daqui, as portas em memória e as fábricas de planta.
"""
from datetime import UTC, date, datetime
from types import TracebackType
from typing import Self
from uuid import uuid4

from src.modules.garden.domain.entities.care_schedule import CareSchedule, CareType
from src.modules.garden.domain.entities.user_plant import (
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.modules.garden.domain.ports.user_plant_repository import IUserPlantRepository
from src.modules.garden.domain.services.plant_lookup import IPlantLookup
from src.modules.garden.domain.value_objects.care_interval import CareInterval
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.modules.identification import IdentificationId
from src.shared.domain import LocalCalendar, UserId

CALENDAR = LocalCalendar.from_name("America/Sao_Paulo")


def make_care_schedule(next_due_on: date | None = None) -> CareSchedule:
    return CareSchedule(
        care_type=CareType.WATER,
        interval=CareInterval(days=7),
        is_active=True,
        created_at=datetime.now(UTC),
        next_due_on=next_due_on,
    )


def make_user_plant(
    user_id: UserId | None = None,
    care_schedule: CareSchedule | None = None,
    identification_id: IdentificationId | None = None,
    scientific_name: str = "Monstera deliciosa",
) -> UserPlant:
    return UserPlant(
        id=UserPlantId(uuid4()),
        user_id=user_id or UserId(uuid4()),
        scientific_name=scientific_name,
        identification_confidence=0.9,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        care_schedule=care_schedule or make_care_schedule(),
        identification_id=identification_id or IdentificationId(uuid4()),
        added_at=datetime.now(UTC),
    )


class InMemoryUserPlantRepository(IUserPlantRepository):
    """Plantas por ID; as apagadas (soft delete) ficam em `removed` e somem das consultas."""

    def __init__(self, *plants: UserPlant) -> None:
        self.by_id: dict[UserPlantId, UserPlant] = {plant.id: plant for plant in plants}
        self.removed: set[UserPlantId] = set()
        self.saved: list[UserPlantId] = []

    def _active(self) -> list[UserPlant]:
        return [plant for plant in self.by_id.values() if plant.id not in self.removed]

    async def save(self, user_plant: UserPlant) -> UserPlant:
        self.by_id[user_plant.id] = user_plant
        self.saved.append(user_plant.id)
        return user_plant

    async def get_by_id(self, user_plant_id: UserPlantId, user_id: UserId | None = None) -> UserPlant | None:
        return next(
            (p for p in self._active() if p.id == user_plant_id and (user_id is None or p.user_id == user_id)),
            None,
        )

    async def list_by_user(self, user_id: UserId) -> list[UserPlant]:
        return [plant for plant in self._active() if plant.user_id == user_id]

    async def delete(self, user_plant_id: UserPlantId, user_id: UserId) -> bool:
        if await self.get_by_id(user_plant_id, user_id) is None:
            return False
        self.removed.add(user_plant_id)
        return True

    async def count_by_user(self, user_id: UserId) -> int:
        return len(await self.list_by_user(user_id))

    async def get_by_identification(self, identification_id: IdentificationId, user_id: UserId) -> UserPlant | None:
        return next(
            (p for p in self._active() if p.identification_id == identification_id and p.user_id == user_id),
            None,
        )

    async def list_with_streak_due_before(self, due_before: date) -> list[UserPlant]:
        return [
            plant for plant in self._active()
            if plant.watering_streak.current_count > 0
            and plant.care_schedule.next_due_on is not None
            and plant.care_schedule.next_due_on < due_before
        ]


class FakeGardenUnitOfWork(IGardenUnitOfWork):
    """Plantas em memória (gravadas na hora, sem rollback), transações abertas e commits."""

    def __init__(self, user_plants: InMemoryUserPlantRepository | None = None) -> None:
        self.user_plants: InMemoryUserPlantRepository = user_plants or InMemoryUserPlantRepository()
        self.opened = 0
        self.commits = 0

    @property
    def joined(self) -> bool:
        return False

    async def __aenter__(self) -> Self:
        self.opened += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakePlantLookup(IPlantLookup):
    """As plantas dadas estão no jardim, cada uma só para o próprio dono."""

    def __init__(self, *plants: UserPlant) -> None:
        self._repository = InMemoryUserPlantRepository(*plants)

    async def get_for_user(self, user_plant_id: UserPlantId, user_id: UserId) -> UserPlant:
        plant = await self._repository.get_by_id(user_plant_id, user_id)
        if plant is None:
            raise PlantNotFoundError(user_plant_id)
        return plant
