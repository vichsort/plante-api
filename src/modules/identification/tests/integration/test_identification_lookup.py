"""Identificações gravadas no Postgres real, com as FKs de verdade (usuário, espécie, amostra de treino)."""
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.catalog import PlantSpeciesId
from src.modules.identification.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentificationUnitOfWork,
)
from src.modules.identification.domain.entities.identification import Identification
from src.modules.identification.domain.exceptions import IdentificationNotFoundError
from src.modules.identification.domain.services.identification_lookup import (
    IdentificationLookup,
)
from src.modules.identification.tests.fakes import make_identification
from src.modules.training import TrainingIdentificationSampleId
from src.shared.domain import UserId

# O que as FKs da identificação exigem, gravado direto: as tabelas são de outros módulos, e um
# teste daqui só enxerga a API pública deles
_PREREQUISITES = """
INSERT INTO users (id, email, hashed_password, location_country, location_state, is_verified, created_at, updated_at)
VALUES (:user_id, :email, 'h', 'BR', 'SP', true, now(), now());
INSERT INTO plant_species (id, scientific_name, enrichment_status, created_at, updated_at)
VALUES (:species_id, :species_name, 'pending', now(), now());
INSERT INTO training_identification_samples
    (id, image_key, scientific_name, source, confidence, low_confidence, signals, period, country, state)
VALUES (:sample_id, 'training/identifications/1.jpg', :species_name, 'consensus', 0.9, false, '[]', date_trunc('month', now()), 'BR', 'SP');
"""


async def _saved_identification(session_factory: async_sessionmaker[AsyncSession]) -> Identification:
    user_id, species_id, sample_id = uuid4(), uuid4(), uuid4()
    async with session_factory() as session:
        for statement in filter(str.strip, _PREREQUISITES.split(";")):
            await session.execute(text(statement), {
                "user_id": user_id, "email": f"{user_id}@plante.org", "species_id": species_id,
                "species_name": f"Monstera {species_id}", "sample_id": sample_id,
            })
        await session.commit()

    identification = replace(
        make_identification(user_id=UserId(user_id)),
        species_id=PlantSpeciesId(species_id),
        training_sample_id=TrainingIdentificationSampleId(sample_id),
    )
    async with SqlAlchemyIdentificationUnitOfWork(session_factory) as uow:
        saved = await uow.identifications.save(identification)
        await uow.commit()
    return saved


async def test_owner_finds_the_identification(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    identification = await _saved_identification(session_factory)
    lookup = IdentificationLookup(SqlAlchemyIdentificationUnitOfWork(session_factory))

    # Act
    found = await lookup.get_for_user(identification.id, identification.user_id)

    # Assert
    assert found == identification


async def test_someone_else_does_not_find_the_identification(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    identification = await _saved_identification(session_factory)
    lookup = IdentificationLookup(SqlAlchemyIdentificationUnitOfWork(session_factory))

    # Act & Assert: a API não distingue "não existe" de "é de outro usuário"
    with pytest.raises(IdentificationNotFoundError):
        await lookup.get_for_user(identification.id, UserId(uuid4()))
