from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain.entities.identification import Identification
from src.domain.entities.training import FeedbackOrigin, FeedbackVerdict
from src.domain.entities.user_plant import IdentificationSource, UserPlant
from src.domain.exceptions import (
    IdentificationNotFoundError,
    PlantLimitExceededError,
    PlantNotFoundError,
)
from src.domain.use_cases.add_plant_to_garden_use_case import (
    AddPlantToGardenInputDTO,
    AddPlantToGardenUseCase,
)
from src.domain.use_cases.break_streak_cron_use_case import BreakStreakCronUseCase
from src.domain.use_cases.delete_user_plant_use_case import (
    DeleteUserPlantInputDTO,
    DeleteUserPlantUseCase,
)
from src.domain.use_cases.get_user_garden_use_case import (
    GetUserGardenInputDTO,
    GetUserGardenUseCase,
)
from src.domain.use_cases.water_plant_use_case import (
    WaterPlantInputDTO,
    WaterPlantUseCase,
)
from src.domain.value_objects.ids import (
    IdentificationId,
    PlantSpeciesId,
    TrainingIdentificationSampleId,
    UserPlantId,
)
from src.domain.value_objects.sources import IdentificationOrigin
from src.domain.value_objects.streak import Streak
from src.shared.domain import UserId
from tests.factories import (
    CALENDAR,
    make_care_schedule,
    make_identification,
    make_user,
    make_user_plant,
)
from tests.fakes import FakeUnitOfWork


def _garden_use_case(identification: Identification | None, existing: UserPlant | None = None, plants_in_garden: int = 0):
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = make_user()
    identifications = AsyncMock()
    identifications.get_for_user.return_value = identification
    user_plants = AsyncMock()
    user_plants.get_by_identification.return_value = existing
    user_plants.count_by_user.return_value = plants_in_garden
    user_plants.save.side_effect = lambda plant: plant
    training = AsyncMock()
    uow = FakeUnitOfWork(users=user_repo, identifications=identifications, user_plants=user_plants, training=training)
    publisher = AsyncMock()
    return AddPlantToGardenUseCase(uow=uow, publisher=publisher, calendar=CALENDAR), uow, publisher


def _identification(source: IdentificationOrigin = "consensus") -> Identification:
    identification = make_identification(
        user_id=UserId(uuid4()),
        training_sample_id=TrainingIdentificationSampleId(uuid4()),
        species_id=PlantSpeciesId(uuid4()),
    )
    return replace(identification, source=source)


@pytest.mark.asyncio
async def test_add_plant_to_garden_creates_plant_from_identification():
    identification = _identification()
    use_case, uow, publisher = _garden_use_case(identification)

    item = await use_case.execute(AddPlantToGardenInputDTO(
        user_id=identification.user_id, identification_id=identification.id, nickname="Clotilde",
    ))
    plant = item.plant

    assert plant.identification_id == identification.id
    assert plant.scientific_name == identification.scientific_name
    assert plant.primary_image_url == identification.image_key
    assert plant.nickname == "Clotilde"
    assert item.needs_watering is False  # nunca regada: ainda não tem vencimento
    assert uow.committed
    publisher.publish.assert_called_once()


@pytest.mark.asyncio
async def test_adding_to_garden_is_an_implicit_positive_signal():
    identification = _identification()
    use_case, uow, _ = _garden_use_case(identification)

    await use_case.execute(AddPlantToGardenInputDTO(user_id=identification.user_id, identification_id=identification.id))

    feedback = uow.training.add_feedback.call_args.args[0]
    assert feedback.identification_sample_id == identification.training_sample_id
    assert (feedback.verdict, feedback.origin) == (FeedbackVerdict.CORRECT, FeedbackOrigin.ADDED_TO_GARDEN)


@pytest.mark.asyncio
async def test_adding_same_identification_twice_returns_existing_plant():
    identification = _identification()
    existing = make_user_plant(user_id=identification.user_id, identification_id=identification.id)
    use_case, uow, publisher = _garden_use_case(identification, existing=existing)

    item = await use_case.execute(AddPlantToGardenInputDTO(user_id=identification.user_id, identification_id=identification.id))

    assert item.plant is existing
    uow.user_plants.save.assert_not_called()
    uow.training.add_feedback.assert_not_called()
    publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_garden_limit_uses_active_plant_count():
    identification = _identification()
    use_case, uow, _ = _garden_use_case(identification, plants_in_garden=3)  # limite do FREE

    with pytest.raises(PlantLimitExceededError):
        await use_case.execute(AddPlantToGardenInputDTO(user_id=identification.user_id, identification_id=identification.id))
    assert not uow.committed


@pytest.mark.asyncio
async def test_identification_of_another_user_is_not_found():
    use_case, _, _ = _garden_use_case(identification=None)

    with pytest.raises(IdentificationNotFoundError):
        await use_case.execute(AddPlantToGardenInputDTO(user_id=UserId(uuid4()), identification_id=IdentificationId(uuid4())))


@pytest.mark.asyncio
@pytest.mark.parametrize("origin, expected", [
    ("kindwise", IdentificationSource.KINDWISE),
    ("plantnet", IdentificationSource.PLANTNET),  # antes virava CONSENSUS
    ("consensus", IdentificationSource.CONSENSUS),
    ("consensus_partial", IdentificationSource.CONSENSUS),
])
async def test_plant_source_follows_identification_origin(origin: IdentificationOrigin, expected: IdentificationSource):
    identification = _identification(source=origin)
    use_case, _, _ = _garden_use_case(identification)

    item = await use_case.execute(AddPlantToGardenInputDTO(user_id=identification.user_id, identification_id=identification.id))

    assert item.plant.identification_source == expected


@pytest.mark.asyncio
async def test_deleting_plant_does_not_touch_identification_or_training():
    user_plants = AsyncMock()
    user_plants.delete.return_value = True
    uow = FakeUnitOfWork(user_plants=user_plants)

    await DeleteUserPlantUseCase(uow=uow).execute(DeleteUserPlantInputDTO(user_id=UserId(uuid4()), user_plant_id=UserPlantId(uuid4())))

    assert uow.committed
    assert uow.identifications.mock_calls == []
    assert uow.training.mock_calls == []


@pytest.mark.asyncio
async def test_deleting_missing_plant_raises_not_found():
    user_plants = AsyncMock()
    user_plants.delete.return_value = False

    with pytest.raises(PlantNotFoundError):
        await DeleteUserPlantUseCase(uow=FakeUnitOfWork(user_plants=user_plants)).execute(
            DeleteUserPlantInputDTO(user_id=UserId(uuid4()), user_plant_id=UserPlantId(uuid4()))
        )


@pytest.mark.asyncio
async def test_water_plant_use_case_success():
    today = CALENDAR.date_of(datetime.now(UTC))
    user_plant = make_user_plant(care_schedule=make_care_schedule(next_due_on=today - timedelta(days=1)))

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = user_plant

    publisher = AsyncMock()

    use_case = WaterPlantUseCase(uow=FakeUnitOfWork(user_plants=user_plant_repo), publisher=publisher, calendar=CALENDAR)

    result = await use_case.execute(WaterPlantInputDTO(
        user_id=user_plant.user_id,
        user_plant_id=user_plant.id,
    ))

    assert result.id == user_plant.id
    assert result.last_watered_at is not None
    user_plant_repo.save.assert_called_once_with(user_plant)
    publisher.publish.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_garden_use_case():
    plant = make_user_plant()
    plant.nickname = "Clotilde"
    user_plant_repo = AsyncMock()
    user_plant_repo.list_by_user.return_value = [plant]

    use_case = GetUserGardenUseCase(uow=FakeUnitOfWork(user_plants=user_plant_repo), calendar=CALENDAR)
    items = await use_case.execute(GetUserGardenInputDTO(user_id=plant.user_id))

    assert [item.plant for item in items] == [plant]
    assert items[0].plant.display_name == "Clotilde"


def _cron(plants: list[UserPlant]) -> tuple[BreakStreakCronUseCase, FakeUnitOfWork, AsyncMock]:
    user_plants = AsyncMock()
    user_plants.list_with_streak_due_before.return_value = plants
    uow = FakeUnitOfWork(user_plants=user_plants)
    publisher = AsyncMock()
    return BreakStreakCronUseCase(uow=uow, publisher=publisher, calendar=CALENDAR), uow, publisher


def _plant_due(due: date, streak: int = 3) -> UserPlant:
    plant = make_user_plant(care_schedule=make_care_schedule(next_due_on=due))
    plant.watering_streak = Streak(current_count=streak)
    return plant


@pytest.mark.asyncio
async def test_cron_breaks_streak_of_plants_that_missed_the_window():
    # Arrange
    today = CALENDAR.date_of(datetime.now(UTC))
    missed = _plant_due(today - timedelta(days=2))
    use_case, uow, publisher = _cron([missed])

    # Act
    result = await use_case.execute()

    # Assert
    assert (result.processed, result.broken) == (1, 1)
    assert missed.watering_streak.current_count == 0
    uow.user_plants.list_with_streak_due_before.assert_called_once_with(today - timedelta(days=1))
    uow.user_plants.save.assert_called_once_with(missed)
    assert uow.committed
    event = publisher.publish.call_args.args[0]
    assert (event.user_plant_id, event.last_streak_count) == (missed.id, 3)


@pytest.mark.asyncio
async def test_cron_keeps_streak_while_the_window_is_open():
    # Arrange: venceu ontem, ainda pode regar hoje
    today = CALENDAR.date_of(datetime.now(UTC))
    still_open = _plant_due(today - timedelta(days=1))
    use_case, uow, publisher = _cron([still_open])

    # Act
    result = await use_case.execute()

    # Assert
    assert result.broken == 0
    assert still_open.watering_streak.current_count == 3
    uow.user_plants.save.assert_not_called()
    publisher.publish.assert_not_called()
