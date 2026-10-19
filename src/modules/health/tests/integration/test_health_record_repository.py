"""Diagnósticos gravados no Postgres real, com as FKs de verdade (usuário, planta e amostra de treino)."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.garden import UserPlantId
from src.modules.health.adapters.persistence.unit_of_work import (
    SqlAlchemyHealthUnitOfWork,
)
from src.modules.health.domain.entities.health_record import HealthRecord
from src.modules.health.tests.fakes import make_health_record
from src.modules.training import TrainingHealthSampleId
from src.shared.domain import UserId

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)

# O que as FKs do diagnóstico exigem, gravado direto: as tabelas são de outros módulos, e um teste
# daqui só enxerga a API pública deles
_PLANT = """
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
INSERT INTO user_plants
    (id, user_id, identification_id, scientific_name, identification_confidence, identification_source, status, added_at,
     streak_count, care_type, care_interval_days, care_is_active, care_climate_adjusted, care_created_at, created_at, updated_at)
VALUES (:plant_id, :user_id, :identification_id, :species_name, 0.9, 'consensus', 'identified', now(),
        0, 'water', 7, true, false, now(), now(), now());
"""
_HEALTH_SAMPLE = """
INSERT INTO training_health_samples
    (id, image_key, scientific_name, vitality_score, severity, source, issues_detected, treatment_plan,
     reference_image_keys, signals, period, country, state)
VALUES (:sample_id, 'training/health/1.jpg', 'Monstera deliciosa', 0.4, 'moderate', 'kindwise', '[]', '[]', '[]',
        '{"provider": "kindwise", "is_healthy_probability": 0.4, "diseases": []}', date_trunc('month', now()), 'BR', 'SP');
"""


async def _execute(session_factory: async_sessionmaker[AsyncSession], statements: str, params: dict[str, object]) -> None:
    async with session_factory() as session:
        for statement in filter(str.strip, statements.split(";")):
            await session.execute(text(statement), params)
        await session.commit()


async def _owner_with_plant(session_factory: async_sessionmaker[AsyncSession]) -> tuple[UserId, UserPlantId]:
    user_id, plant_id, species_id = uuid4(), uuid4(), uuid4()
    await _execute(session_factory, _PLANT, {
        "user_id": user_id, "email": f"{user_id}@plante.org", "species_id": species_id,
        "species_name": f"Monstera {species_id}", "sample_id": uuid4(), "identification_id": uuid4(), "plant_id": plant_id,
    })
    return UserId(user_id), UserPlantId(plant_id)


async def _saved_record(
    session_factory: async_sessionmaker[AsyncSession], user_id: UserId, plant_id: UserPlantId, diagnosed_at: datetime = NOW,
) -> HealthRecord:
    sample_id: UUID = uuid4()
    await _execute(session_factory, _HEALTH_SAMPLE, {"sample_id": sample_id})
    record = make_health_record(
        user_id=user_id, user_plant_id=plant_id, training_sample_id=TrainingHealthSampleId(sample_id), diagnosed_at=diagnosed_at,
    )
    async with SqlAlchemyHealthUnitOfWork(session_factory) as uow:
        saved = await uow.health_records.save(record)
        await uow.commit()
    return saved


async def test_saved_record_is_found_only_by_its_owner(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    user_id, plant_id = await _owner_with_plant(session_factory)
    record = await _saved_record(session_factory, user_id, plant_id)

    # Act
    async with SqlAlchemyHealthUnitOfWork(session_factory) as uow:
        mine = await uow.health_records.get_for_user(record.id, user_id)
        someone_elses = await uow.health_records.get_for_user(record.id, UserId(uuid4()))

    # Assert
    assert mine == record
    assert someone_elses is None


async def test_history_is_newest_first_and_limited(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    user_id, plant_id = await _owner_with_plant(session_factory)
    oldest, middle, newest = [
        await _saved_record(session_factory, user_id, plant_id, NOW - timedelta(days=days)) for days in (14, 7, 0)
    ]
    other_user, other_plant = await _owner_with_plant(session_factory)
    await _saved_record(session_factory, other_user, other_plant)

    # Act
    async with SqlAlchemyHealthUnitOfWork(session_factory) as uow:
        everything = await uow.health_records.list_by_plant(plant_id)
        latest_two = await uow.health_records.list_by_plant(plant_id, limit=2)

    # Assert
    assert [r.id for r in everything] == [newest.id, middle.id, oldest.id]
    assert [r.id for r in latest_two] == [newest.id, middle.id]


async def test_saving_again_updates_the_row(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    user_id, plant_id = await _owner_with_plant(session_factory)
    record = await _saved_record(session_factory, user_id, plant_id)

    # Act
    async with SqlAlchemyHealthUnitOfWork(session_factory) as uow:
        await uow.health_records.save(replace(record, notes="revisto"))
        await uow.commit()

    # Assert
    async with SqlAlchemyHealthUnitOfWork(session_factory) as uow:
        loaded = await uow.health_records.get_for_user(record.id, user_id)
    assert loaded is not None and loaded.notes == "revisto"
