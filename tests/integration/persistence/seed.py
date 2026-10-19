"""Pré-requisitos gravados no banco para os testes de persistência (respeitando as FKs)."""
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.adapters.persistence.repositories.plant_species import (
    PlantSpeciesRepository,
)
from src.modules.identification import Identification
from src.modules.identification.adapters.persistence.repositories.identification import (
    IdentificationRepository,
)
from src.modules.training import TrainingHealthSample
from src.modules.training.adapters.persistence.repositories.training import (
    TrainingRepository,
)
from src.shared.domain import UserId
from tests.factories import (
    make_identification,
    make_species,
    make_training_health_sample,
    make_training_identification_sample,
)


async def seed_identification(
    session: AsyncSession, user_id: UserId, scientific_name: str = "Monstera deliciosa"
) -> Identification:
    """Espécie + amostra de treino + identificação: o que uma planta do jardim exige."""
    species_repo = PlantSpeciesRepository(session)
    species = await species_repo.get_by_scientific_name(scientific_name)
    if species is None:
        species = await species_repo.save(make_species(scientific_name))
    training = make_training_identification_sample(scientific_name)
    await TrainingRepository(session).add_identification_sample(training)
    return await IdentificationRepository(session).save(
        make_identification(user_id=user_id, training_sample_id=training.id, species_id=species.id, scientific_name=scientific_name)
    )


async def seed_training_health_sample(session: AsyncSession) -> TrainingHealthSample:
    sample = make_training_health_sample()
    await TrainingRepository(session).add_health_sample(sample)
    return sample
