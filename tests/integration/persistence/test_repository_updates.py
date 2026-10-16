"""`save` de entidade já persistida atualiza a linha (antes fazia INSERT e violava a PK)."""
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.repositories.health_record_repository import (
    HealthRecordRepository,
)
from src.adapters.persistence.repositories.plant_species_repository import (
    PlantSpeciesRepository,
)
from src.adapters.persistence.repositories.training_repository import TrainingRepository
from src.adapters.persistence.repositories.user_plant_repository import (
    UserPlantRepository,
)
from src.adapters.persistence.repositories.user_repository import UserRepository
from src.domain.entities.plant_species import PlantSpecies
from src.domain.entities.user import User
from src.domain.value_objects.subscription_tier import FeatureCost
from src.domain.value_objects.user_location import UserLocation
from tests.factories import (
    make_health_record,
    make_user,
    make_user_plant,
)
from tests.integration.persistence.seed import (
    seed_identification,
    seed_training_health_sample,
)


async def test_saving_existing_user_updates_it(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.save(User.create_new(
        email="update@plante.org",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        current_time=datetime.now(UTC),
    ))
    await db_session.commit()

    loaded = await repo.get_by_id(user.id)
    assert loaded is not None
    loaded.consume_tokens(FeatureCost.IDENTIFY, date(2026, 10, 16))
    await repo.save(loaded)
    await db_session.commit()

    reloaded = await repo.get_by_id(user.id)
    assert reloaded is not None
    assert (reloaded.tokens_used_today, reloaded.tokens_day) == (1, date(2026, 10, 16))


async def test_saving_new_species_maps_provider_entity_id(db_session: AsyncSession) -> None:
    repo = PlantSpeciesRepository(db_session)
    species = PlantSpecies.create_skeleton("Monstera deliciosa", genus="Monstera", provider_entity_id="ad11b3384dd5c143")

    await repo.save(species)
    await db_session.commit()

    loaded = await repo.get_by_scientific_name("Monstera deliciosa")
    assert loaded is not None
    assert loaded.id == species.id
    assert loaded.provider_entity_id == "ad11b3384dd5c143"


async def test_saving_health_record_with_training_sample(db_session: AsyncSession) -> None:
    user = await UserRepository(db_session).save(make_user(email="health@plante.org"))
    identification = await seed_identification(db_session, user.id)
    plant = await UserPlantRepository(db_session).save(make_user_plant(user_id=user.id, identification_id=identification.id))
    training = await seed_training_health_sample(db_session)
    record = make_health_record(user_id=user.id, user_plant_id=plant.id, training_sample_id=training.id)

    await HealthRecordRepository(db_session).save(record)
    await db_session.commit()

    loaded = await HealthRecordRepository(db_session).get_by_id(record.id)
    assert loaded is not None
    assert loaded.user_id == user.id
    assert loaded.training_sample_id == training.id
    stored = await TrainingRepository(db_session).get_health_sample(training.id)
    assert stored == training
