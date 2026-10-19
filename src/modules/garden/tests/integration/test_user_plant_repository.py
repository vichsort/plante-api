"""Plantas gravadas no Postgres real, com as FKs de verdade (usuário e identificação de origem)."""
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.garden.adapters.persistence.unit_of_work import (
    SqlAlchemyGardenUnitOfWork,
)
from src.modules.garden.domain.entities.user_plant import UserPlant
from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.services.plant_lookup import PlantLookup
from src.modules.garden.domain.value_objects.streak import Streak
from src.modules.garden.tests.fakes import CALENDAR, make_care_schedule, make_user_plant
from src.modules.identification import IdentificationId
from src.shared.domain import UserId

# O que as FKs da planta exigem, gravado direto: as tabelas são de outros módulos, e um teste
# daqui só enxerga a API pública deles
_PREREQUISITES = """
INSERT INTO users (id, email, hashed_password, location_country, location_state, is_verified, created_at, updated_at)
VALUES (:user_id, :email, 'h', 'BR', 'SP', true, now(), now());
INSERT INTO plant_species (id, scientific_name, enrichment_status, created_at, updated_at)
VALUES (:species_id, :species_name, 'pending', now(), now());
INSERT INTO training_identification_samples
    (id, image_key, scientific_name, source, confidence, low_confidence, signals, period, country, state)
VALUES (:sample_id, 'training/identifications/1.jpg', :species_name, 'consensus', 0.9, false, '[]', date_trunc('month', now()), 'BR', 'SP');
INSERT INTO identifications
    (id, user_id, training_sample_id, species_id, scientific_name, confidence, source, image_key, created_at, updated_at)
VALUES (:identification_id, :user_id, :sample_id, :species_id, :species_name, 0.9, 'consensus', 'identifications/1.jpg', now(), now());
"""


async def _owner_with_identification(session_factory: async_sessionmaker[AsyncSession]) -> tuple[UserId, IdentificationId]:
    user_id, identification_id, species_id = uuid4(), uuid4(), uuid4()
    params = {
        "user_id": user_id, "email": f"{user_id}@plante.org", "species_id": species_id,
        "species_name": f"Monstera {species_id}", "sample_id": uuid4(), "identification_id": identification_id,
    }
    async with session_factory() as session:
        for statement in filter(str.strip, _PREREQUISITES.split(";")):
            await session.execute(text(statement), params)
        await session.commit()
    return UserId(user_id), IdentificationId(identification_id)


async def _saved_plant(session_factory: async_sessionmaker[AsyncSession], due: date | None = None) -> UserPlant:
    user_id, identification_id = await _owner_with_identification(session_factory)
    plant = make_user_plant(user_id=user_id, identification_id=identification_id, care_schedule=make_care_schedule(due))
    plant.nickname = "Clotilde"
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        saved = await uow.user_plants.save(plant)
        await uow.commit()
    return saved


async def test_saved_plant_is_found_by_id_owner_and_identification(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    plant = await _saved_plant(session_factory)

    # Act
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        by_id = await uow.user_plants.get_by_id(plant.id, plant.user_id)
        garden = await uow.user_plants.list_by_user(plant.user_id)
        count = await uow.user_plants.count_by_user(plant.user_id)
        by_identification = await uow.user_plants.get_by_identification(plant.identification_id, plant.user_id)

    # Assert
    assert by_id is not None and by_id.nickname == "Clotilde"
    assert [p.id for p in garden] == [plant.id]
    assert count == 1
    assert by_identification is not None and by_identification.id == plant.id


async def test_saving_again_updates_the_watering(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    plant = await _saved_plant(session_factory)
    plant.water(datetime.now(UTC), CALENDAR)

    # Act
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        await uow.user_plants.save(plant)
        await uow.commit()

    # Assert
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        watered = await uow.user_plants.get_by_id(plant.id)
    assert watered is not None
    assert watered.watering_streak.current_count == 1
    assert watered.care_schedule.next_due_on == plant.care_schedule.next_due_on


async def test_removed_plant_leaves_the_garden(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    plant = await _saved_plant(session_factory)

    # Act
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        removed = await uow.user_plants.delete(plant.id, plant.user_id)
        await uow.commit()

    # Assert: soft delete, a planta some de todas as consultas
    assert removed is True
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        assert await uow.user_plants.get_by_id(plant.id, plant.user_id) is None
        assert await uow.user_plants.list_by_user(plant.user_id) == []
        assert await uow.user_plants.count_by_user(plant.user_id) == 0
        assert await uow.user_plants.get_by_identification(plant.identification_id, plant.user_id) is None


async def test_streak_query_returns_only_running_streaks_due_before_the_day(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    today = CALENDAR.date_of(datetime.now(UTC))
    overdue = await _saved_plant(session_factory, due=today - timedelta(days=3))
    without_streak = await _saved_plant(session_factory, due=today - timedelta(days=3))
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        overdue.watering_streak = Streak(current_count=2)
        await uow.user_plants.save(overdue)
        await uow.commit()

    # Act
    async with SqlAlchemyGardenUnitOfWork(session_factory) as uow:
        due = await uow.user_plants.list_with_streak_due_before(today - timedelta(days=1))

    # Assert
    ids = {plant.id for plant in due}
    assert overdue.id in ids
    assert without_streak.id not in ids


async def test_lookup_finds_only_the_owners_active_plant(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    plant = await _saved_plant(session_factory)
    lookup = PlantLookup(SqlAlchemyGardenUnitOfWork(session_factory))

    # Act
    found = await lookup.get_for_user(plant.id, plant.user_id)

    # Assert
    assert found.id == plant.id
    with pytest.raises(PlantNotFoundError):
        await lookup.get_for_user(plant.id, UserId(uuid4()))
