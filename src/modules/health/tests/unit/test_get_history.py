from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.modules.garden import PlantNotFoundError
from src.modules.garden.tests.fakes import FakePlantLookup, make_user_plant
from src.modules.health.domain.use_cases.get_history import (
    GetHealthHistoryInputDTO,
    GetHealthHistoryUseCase,
)
from src.modules.health.tests.fakes import (
    FakeHealthUnitOfWork,
    InMemoryHealthRecordRepository,
    make_health_record,
)
from src.shared.domain import UserId

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


async def test_history_lists_the_plant_diagnoses_newest_first() -> None:
    # Arrange
    plant = make_user_plant()
    older, newer = (
        make_health_record(user_id=plant.user_id, user_plant_id=plant.id, diagnosed_at=NOW - timedelta(days=days))
        for days in (7, 0)
    )
    other_plant = make_health_record(user_id=plant.user_id)
    uow = FakeHealthUnitOfWork(InMemoryHealthRecordRepository(older, newer, other_plant))

    # Act
    history = await GetHealthHistoryUseCase(uow, FakePlantLookup(plant)).execute(
        GetHealthHistoryInputDTO(user_id=plant.user_id, user_plant_id=plant.id)
    )

    # Assert
    assert [record.id for record in history] == [newer.id, older.id]


async def test_history_of_a_plant_of_another_user_is_not_found() -> None:
    # Arrange
    plant = make_user_plant()
    uow = FakeHealthUnitOfWork(InMemoryHealthRecordRepository(make_health_record(user_id=plant.user_id, user_plant_id=plant.id)))

    # Act & Assert
    with pytest.raises(PlantNotFoundError):
        await GetHealthHistoryUseCase(uow, FakePlantLookup(plant)).execute(
            GetHealthHistoryInputDTO(user_id=UserId(uuid4()), user_plant_id=plant.id)
        )
