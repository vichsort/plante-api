import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.care_schedule import CareSchedule, CareType
from src.domain.entities.plant_identification_sample import (
    PlantIdentificationSample,
    SampleStatus,
)
from src.domain.entities.plant_species import EnrichmentStatus, PlantSpecies
from src.domain.entities.user import User
from src.domain.entities.user_plant import (
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.domain.use_cases.add_plant_to_garden_use_case import (
    AddPlantToGardenInputDTO,
    AddPlantToGardenUseCase,
)
from src.domain.use_cases.get_user_garden_use_case import (
    GetUserGardenInputDTO,
    GetUserGardenUseCase,
)
from src.domain.use_cases.water_plant_use_case import (
    WaterPlantInputDTO,
    WaterPlantUseCase,
)
from src.domain.value_objects.care_interval import CareInterval
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation


@pytest.mark.asyncio
async def test_add_plant_to_garden_success():
    user_id = str(uuid.uuid4())
    user_plant_id = str(uuid.uuid4())
    sample_id = str(uuid.uuid4())
    species_id = str(uuid.uuid4())

    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email="dev@plante.org",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        is_verified=True,
        subscription=SubscriptionTier.FREE,
        created_at=now,
        garden_count=0,
    )

    care = CareSchedule(
        id=1,
        user_plant_id=user_plant_id,
        care_type=CareType.WATER,
        interval=CareInterval(days=2),
        is_active=True,
        next_due_at=now,
        created_at=now,
    )

    user_plant = UserPlant(
        id=user_plant_id,
        user_id=user_id,
        scientific_name="Monstera deliciosa",
        identification_confidence=0.9,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        added_at=now,
        care_schedule=care,
    )

    species = PlantSpecies(
        id=species_id,
        scientific_name="Monstera deliciosa",
        enrichment_status=EnrichmentStatus.PENDING,
    )

    sample = PlantIdentificationSample(
        id=sample_id,
        scientific_name="Monstera deliciosa",
        species_id=species_id,
        user_image_key="key",
        identification_confidence=0.9,
        identification_source="consensus",
        raw_response={},
        status=SampleStatus.PENDING,
        created_at=now,
        user_id=user_id,
    )

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = user_plant

    species_repo = AsyncMock()
    species_repo.get_by_scientific_name.return_value = species

    sample_repo = AsyncMock()
    sample_repo.get_by_id.return_value = sample

    publisher = AsyncMock()

    use_case = AddPlantToGardenUseCase(
        user_repo=user_repo,
        user_plant_repo=user_plant_repo,
        species_repo=species_repo,
        sample_repo=sample_repo,
        publisher=publisher,
    )

    await use_case.execute(AddPlantToGardenInputDTO(
        user_id=user_id,
        user_plant_id=user_plant_id,
        sample_id=sample_id,
    ))

    assert user.garden_count == 1
    user_repo.save.assert_called_once_with(user)
    sample_repo.save.assert_called_once()
    publisher.publish.assert_called_once()

@pytest.mark.asyncio
async def test_water_plant_use_case_success():
    user_id = str(uuid.uuid4())
    user_plant_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    care = CareSchedule(
        id=1,
        user_plant_id=user_plant_id,
        care_type=CareType.WATER,
        interval=CareInterval(days=2),
        is_active=True,
        next_due_at=now - timedelta(days=1),
        created_at=now - timedelta(days=10),
    )

    user_plant = UserPlant(
        id=user_plant_id,
        user_id=user_id,
        scientific_name="Monstera deliciosa",
        identification_confidence=0.9,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        added_at=now - timedelta(days=10),
        care_schedule=care,
    )

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = user_plant

    publisher = AsyncMock()

    use_case = WaterPlantUseCase(user_plant_repo=user_plant_repo, publisher=publisher)

    result = await use_case.execute(WaterPlantInputDTO(
        user_id=user_id,
        user_plant_id=user_plant_id,
    ))

    assert result["user_plant_id"] == user_plant_id
    assert result["last_watered_at"] is not None
    user_plant_repo.save.assert_called_once_with(user_plant)
    publisher.publish.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_garden_use_case():
    user_id = str(uuid.uuid4())
    user_plant_repo = AsyncMock()
    user_plant_repo.get_garden_view_for_user.return_value = [
        {
            "id": str(uuid.uuid4()),
            "scientific_name": "Monstera deliciosa",
            "nickname": "Clotilde",
            "display_name": "Clotilde",
            "primary_image_url": "http://img",
            "last_watered_at": None,
            "next_due_at": None,
            "needs_watering": True,
            "streak_count": 0,
        }
    ]

    use_case = GetUserGardenUseCase(user_plant_repo=user_plant_repo)
    items = await use_case.execute(GetUserGardenInputDTO(user_id=user_id))

    assert len(items) == 1
    assert items[0]["nickname"] == "Clotilde"
