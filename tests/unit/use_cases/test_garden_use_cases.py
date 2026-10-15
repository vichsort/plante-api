from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

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
from tests.factories import (
    make_care_schedule,
    make_identification_sample,
    make_species,
    make_user,
    make_user_plant,
)


@pytest.mark.asyncio
async def test_add_plant_to_garden_success():
    user = make_user(garden_count=0)
    user_plant = make_user_plant(user_id=user.id)
    sample = make_identification_sample(user_id=user.id)

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = user_plant

    species_repo = AsyncMock()
    species_repo.get_by_scientific_name.return_value = make_species()

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
        user_id=user.id,
        user_plant_id=user_plant.id,
        sample_id=sample.id,
    ))

    assert user.garden_count == 1
    user_repo.save.assert_called_once_with(user)
    sample_repo.save.assert_called_once()
    publisher.publish.assert_called_once()

@pytest.mark.asyncio
async def test_water_plant_use_case_success():
    now = datetime.now(UTC)
    user_plant = make_user_plant(care_schedule=make_care_schedule(next_due_at=now - timedelta(days=1)))

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = user_plant

    publisher = AsyncMock()

    use_case = WaterPlantUseCase(user_plant_repo=user_plant_repo, publisher=publisher)

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

    use_case = GetUserGardenUseCase(user_plant_repo=user_plant_repo)
    items = await use_case.execute(GetUserGardenInputDTO(user_id=plant.user_id))

    assert items == [plant]
    assert items[0].display_name == "Clotilde"
