from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.modules.catalog import PlantSpecies
from src.modules.catalog.tests.fakes import FakeSpeciesRegistry
from src.modules.garden.domain.entities.user_plant import (
    IdentificationSource,
    UserPlant,
)
from src.modules.garden.domain.events import (
    PlantAddedToGardenEvent,
    PlantWateredEvent,
    StreakBrokenEvent,
)
from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.use_cases.add_plant import (
    AddPlantToGardenInputDTO,
    AddPlantToGardenUseCase,
)
from src.modules.garden.domain.use_cases.break_missed_streaks import (
    BreakStreakCronUseCase,
)
from src.modules.garden.domain.use_cases.delete_plant import (
    DeleteUserPlantInputDTO,
    DeleteUserPlantUseCase,
)
from src.modules.garden.domain.use_cases.get_garden import (
    GetUserGardenInputDTO,
    GetUserGardenUseCase,
)
from src.modules.garden.domain.use_cases.get_plant_details import (
    GetPlantDetailsInputDTO,
    GetPlantDetailsUseCase,
)
from src.modules.garden.domain.use_cases.water_plant import (
    WaterPlantInputDTO,
    WaterPlantUseCase,
)
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.modules.garden.domain.value_objects.removal_reason import RemovalReason
from src.modules.garden.domain.value_objects.streak import Streak
from src.modules.garden.tests.fakes import (
    CALENDAR,
    FakeGardenUnitOfWork,
    InMemoryUserPlantRepository,
    make_care_schedule,
    make_user_plant,
)
from src.modules.identification import (
    Identification,
    IdentificationId,
    IdentificationNotFoundError,
)
from src.modules.identification.tests.fakes import (
    FakeIdentificationLookup,
    make_identification,
)
from src.modules.identity.tests.fakes import FakeUserDirectory
from src.modules.quota import PlantLimitExceededError
from src.modules.quota.tests.fakes import FakeGardenQuota
from src.modules.training import (
    FeedbackOrigin,
    FeedbackVerdict,
    IdentificationLabel,
    IdentificationOrigin,
)
from src.modules.training.tests.fakes import FakeTrainingRecorder
from src.shared.domain import UserId
from src.shared.tests.fakes import RecordingPublisher

OWNER = UserId(UUID(int=1))


def _today() -> date:
    return CALENDAR.date_of(datetime.now(UTC))


# --- Adicionar ao jardim ------------------------------------------------------------------------

@dataclass
class _Add:
    """O `AddPlantToGardenUseCase` com as portas em memória."""
    identification: Identification = field(default_factory=lambda: make_identification(user_id=OWNER))
    plants: InMemoryUserPlantRepository = field(default_factory=InMemoryUserPlantRepository)
    publisher: RecordingPublisher = field(default_factory=RecordingPublisher)
    training: FakeTrainingRecorder = field(default_factory=FakeTrainingRecorder)
    uow: FakeGardenUnitOfWork = field(init=False)

    def __post_init__(self) -> None:
        self.uow = FakeGardenUnitOfWork(self.plants)

    async def run(self, identification_id: IdentificationId | None = None, nickname: str | None = None) -> UserPlant:
        use_case = AddPlantToGardenUseCase(
            uow=self.uow, publisher=self.publisher, calendar=CALENDAR, users=FakeUserDirectory(), quota=FakeGardenQuota(),
            training=self.training, identifications=FakeIdentificationLookup(self.identification),
        )
        item = await use_case.execute(AddPlantToGardenInputDTO(
            user_id=OWNER, identification_id=identification_id or self.identification.id, nickname=nickname,
        ))
        return item.plant


async def test_add_creates_the_plant_from_the_identification() -> None:
    # Arrange
    add = _Add()

    # Act
    plant = await add.run(nickname="Clotilde")

    # Assert
    assert plant.identification_id == add.identification.id
    assert (plant.scientific_name, plant.primary_image_url) == (add.identification.scientific_name, add.identification.image_key)
    assert plant.nickname == "Clotilde"
    assert plant.needs_watering(_today()) is False  # nunca regada: ainda não tem vencimento
    assert add.uow.commits == 1
    (event,) = add.publisher.events
    assert isinstance(event, PlantAddedToGardenEvent) and event.is_first_plant


async def test_adding_is_an_implicit_positive_signal() -> None:
    # Arrange
    add = _Add()

    # Act
    await add.run()

    # Assert
    (feedback,) = add.training.feedback
    assert feedback.target == IdentificationLabel(add.identification.training_sample_id)
    assert (feedback.verdict, feedback.origin) == (FeedbackVerdict.CORRECT, FeedbackOrigin.ADDED_TO_GARDEN)


async def test_adding_the_same_identification_twice_returns_the_existing_plant() -> None:
    # Arrange
    add = _Add()
    first = await add.run()

    # Act
    second = await add.run()

    # Assert: sem planta nova, sinal novo nem evento novo
    assert second is first
    assert len(add.plants.by_id) == 1
    assert len(add.training.feedback) == 1
    assert len(add.publisher.events) == 1


async def test_garden_limit_counts_the_active_plants() -> None:
    # Arrange: o FREE aceita 3
    plants = InMemoryUserPlantRepository(*(make_user_plant(user_id=OWNER) for _ in range(3)))
    add = _Add(plants=plants)

    # Act & Assert
    with pytest.raises(PlantLimitExceededError):
        await add.run()
    assert add.uow.commits == 0


async def test_identification_of_someone_else_is_not_found() -> None:
    # Arrange
    add = _Add(identification=make_identification(user_id=UserId(uuid4())))

    # Act & Assert
    with pytest.raises(IdentificationNotFoundError):
        await add.run()


@pytest.mark.parametrize(("origin", "expected"), [
    ("kindwise", IdentificationSource.KINDWISE),
    ("plantnet", IdentificationSource.PLANTNET),  # antes virava CONSENSUS
    ("consensus", IdentificationSource.CONSENSUS),
    ("consensus_partial", IdentificationSource.CONSENSUS),
])
async def test_plant_source_follows_the_identification_origin(origin: IdentificationOrigin, expected: IdentificationSource) -> None:
    # Arrange
    add = _Add(identification=make_identification(user_id=OWNER, source=origin))

    # Act
    plant = await add.run()

    # Assert
    assert plant.identification_source == expected


# --- Tirar do jardim ----------------------------------------------------------------------------

@dataclass
class _Delete:
    """The `DeleteUserPlantUseCase` with in-memory ports; the plant comes from an identification."""
    identification: Identification = field(default_factory=lambda: make_identification(user_id=OWNER))
    training: FakeTrainingRecorder = field(default_factory=FakeTrainingRecorder)
    plant: UserPlant = field(init=False)
    uow: FakeGardenUnitOfWork = field(init=False)

    def __post_init__(self) -> None:
        self.plant = make_user_plant(user_id=OWNER, identification_id=self.identification.id)
        self.uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(self.plant))

    async def run(self, reason: RemovalReason | None = None, *identifications: Identification) -> None:
        lookup = FakeIdentificationLookup(*(identifications or (self.identification,)))
        use_case = DeleteUserPlantUseCase(self.uow, self.training, lookup)
        await use_case.execute(DeleteUserPlantInputDTO(user_id=OWNER, user_plant_id=self.plant.id, reason=reason))


async def test_delete_without_a_reason_leaves_the_dataset_alone() -> None:
    # Arrange
    delete = _Delete()

    # Act
    await delete.run()

    # Assert: the plant may have died or been given away; that says nothing about the species
    assert await delete.uow.user_plants.list_by_user(OWNER) == []
    assert delete.uow.commits == 1
    assert delete.training.is_empty


@pytest.mark.parametrize(("reason", "verdict", "origin"), [
    (RemovalReason.MISIDENTIFIED, FeedbackVerdict.WRONG, FeedbackOrigin.REMOVED_MISIDENTIFIED),
    (RemovalReason.DIED, FeedbackVerdict.UNSURE, FeedbackOrigin.REMOVED_DIED),
    (RemovalReason.GAVE_AWAY, FeedbackVerdict.UNSURE, FeedbackOrigin.REMOVED_GAVE_AWAY),
    (RemovalReason.OTHER, FeedbackVerdict.UNSURE, FeedbackOrigin.REMOVED_OTHER),
])
async def test_the_removal_reason_is_an_implicit_signal_and_only_misidentified_votes(
    reason: RemovalReason, verdict: FeedbackVerdict, origin: FeedbackOrigin,
) -> None:
    # Arrange
    delete = _Delete()

    # Act
    await delete.run(reason)

    # Assert
    (feedback,) = delete.training.feedback
    assert feedback.target == IdentificationLabel(delete.identification.training_sample_id)
    assert (feedback.verdict, feedback.origin) == (verdict, origin)
    assert delete.uow.commits == 1


async def test_a_reason_without_its_identification_still_removes_the_plant() -> None:
    # Arrange: the lookup knows no identification for this plant
    delete = _Delete()
    other = make_identification(user_id=OWNER)

    # Act
    await delete.run(RemovalReason.MISIDENTIFIED, other)

    # Assert
    assert await delete.uow.user_plants.list_by_user(OWNER) == []
    assert delete.training.is_empty


async def test_deleting_a_missing_plant_is_not_found() -> None:
    # Arrange
    uow = FakeGardenUnitOfWork()
    use_case = DeleteUserPlantUseCase(uow, FakeTrainingRecorder(), FakeIdentificationLookup())

    # Act & Assert
    with pytest.raises(PlantNotFoundError):
        await use_case.execute(DeleteUserPlantInputDTO(user_id=OWNER, user_plant_id=UserPlantId(uuid4())))


# --- Regar, listar e detalhar -------------------------------------------------------------------

async def test_watering_saves_the_plant_and_publishes_the_streak() -> None:
    # Arrange: venceu ontem, dentro da janela
    plant = make_user_plant(user_id=OWNER, care_schedule=make_care_schedule(next_due_on=_today() - timedelta(days=1)))
    uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(plant))
    publisher = RecordingPublisher()

    # Act
    watered = await WaterPlantUseCase(uow, publisher, CALENDAR).execute(WaterPlantInputDTO(user_id=OWNER, user_plant_id=plant.id))

    # Assert
    assert watered.last_watered_at is not None
    assert uow.user_plants.saved == [plant.id]
    assert uow.commits == 1
    (event,) = publisher.events
    assert isinstance(event, PlantWateredEvent) and event.current_streak == 1


async def test_watering_someone_elses_plant_is_not_found() -> None:
    # Arrange
    plant = make_user_plant(user_id=UserId(uuid4()))
    uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(plant))

    # Act & Assert
    with pytest.raises(PlantNotFoundError):
        await WaterPlantUseCase(uow, RecordingPublisher(), CALENDAR).execute(WaterPlantInputDTO(user_id=OWNER, user_plant_id=plant.id))


async def test_garden_lists_only_the_users_plants() -> None:
    # Arrange
    mine = make_user_plant(user_id=OWNER)
    uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(mine, make_user_plant()))

    # Act
    items = await GetUserGardenUseCase(uow, CALENDAR).execute(GetUserGardenInputDTO(user_id=OWNER))

    # Assert
    assert [item.plant for item in items] == [mine]


async def test_details_bring_the_species_from_the_catalog() -> None:
    # Arrange
    plant = make_user_plant(user_id=OWNER)
    species = PlantSpecies.create_skeleton("Monstera deliciosa", family="Araceae")
    uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(plant))

    # Act
    details = await GetPlantDetailsUseCase(uow, CALENDAR, FakeSpeciesRegistry({"Monstera deliciosa": species})).execute(
        GetPlantDetailsInputDTO(user_id=OWNER, user_plant_id=plant.id),
    )

    # Assert
    assert (details.plant, details.species, details.needs_watering) == (plant, species, False)


async def test_details_of_a_missing_plant_are_not_found() -> None:
    # Arrange
    uow = FakeGardenUnitOfWork()

    # Act & Assert
    with pytest.raises(PlantNotFoundError):
        await GetPlantDetailsUseCase(uow, CALENDAR, FakeSpeciesRegistry()).execute(
            GetPlantDetailsInputDTO(user_id=OWNER, user_plant_id=UserPlantId(uuid4())),
        )


# --- Cron da sequência --------------------------------------------------------------------------

def _plant_due(due: date, streak: int = 3) -> UserPlant:
    plant = make_user_plant(care_schedule=make_care_schedule(next_due_on=due))
    plant.watering_streak = Streak(current_count=streak)
    return plant


async def test_cron_breaks_the_streak_of_plants_that_missed_the_window() -> None:
    # Arrange
    missed = _plant_due(_today() - timedelta(days=2))
    uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(missed))
    publisher = RecordingPublisher()

    # Act
    result = await BreakStreakCronUseCase(uow, publisher, CALENDAR).execute()

    # Assert
    assert (result.processed, result.broken) == (1, 1)
    assert missed.watering_streak.current_count == 0
    assert uow.user_plants.saved == [missed.id]
    assert uow.commits == 1
    (event,) = publisher.events
    assert isinstance(event, StreakBrokenEvent)
    assert (event.user_plant_id, event.last_streak_count) == (missed.id, 3)


async def test_cron_keeps_the_streak_while_the_window_is_open() -> None:
    # Arrange: venceu ontem, ainda pode regar hoje (nem entra na consulta)
    still_open = _plant_due(_today() - timedelta(days=1))
    uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(still_open))
    publisher = RecordingPublisher()

    # Act
    result = await BreakStreakCronUseCase(uow, publisher, CALENDAR).execute()

    # Assert
    assert result.broken == 0
    assert still_open.watering_streak.current_count == 3
    assert uow.user_plants.saved == []
    assert publisher.events == []
