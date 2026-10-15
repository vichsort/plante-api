from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.repositories.user_plant_repository import (
    UserPlantRepository,
)
from src.adapters.persistence.repositories.user_repository import UserRepository
from src.domain.entities.care_schedule import CareSchedule, CareType
from src.domain.entities.user import User
from src.domain.entities.user_plant import (
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.domain.value_objects.care_interval import CareInterval
from src.domain.value_objects.ids import UserPlantId
from src.domain.value_objects.user_location import UserLocation
from tests.integration.persistence.seed import seed_identification


@pytest.mark.asyncio
async def test_user_plant_repository_crud_and_soft_delete(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    plant_repo = UserPlantRepository(db_session)
    now = datetime.now(UTC)

    # 1. Salvar usuário dono no banco real
    user = User.create_new(
        email="garden_owner@plante.org",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        current_time=now,
    )
    saved_user = await user_repo.save(user)
    identification = await seed_identification(db_session, saved_user.id)
    await db_session.commit()

    # 2. Criar e salvar planta do usuário
    care = CareSchedule(
        care_type=CareType.WATER,
        interval=CareInterval(days=2),
        is_active=True,
        next_due_at=now + timedelta(days=2),
        created_at=now,
    )

    plant = UserPlant(
        id=UserPlantId(uuid4()),
        user_id=saved_user.id,
        scientific_name="Monstera deliciosa",
        identification_confidence=0.95,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        added_at=now,
        nickname="Clotilde",
        primary_image_url="http://storage.plante.org/img.jpg",
        care_schedule=care,
        identification_id=identification.id,
    )

    saved_plant = await plant_repo.save(plant)
    await db_session.commit()

    assert saved_plant.id is not None
    assert saved_plant.user_id == saved_user.id
    assert saved_plant.nickname == "Clotilde"

    # 3. Buscar por ID e listar plantas do jardim
    fetched_plant = await plant_repo.get_by_id(saved_plant.id, saved_user.id)
    assert fetched_plant is not None
    assert fetched_plant.scientific_name == "Monstera deliciosa"

    garden_list = await plant_repo.list_by_user(saved_user.id)
    assert len(garden_list) == 1
    assert garden_list[0].id == saved_plant.id

    count = await plant_repo.count_by_user(saved_user.id)
    assert count == 1

    by_identification = await plant_repo.get_by_identification(identification.id, saved_user.id)
    assert by_identification is not None and by_identification.id == saved_plant.id

    # 4. Detalhes com a espécie (gravada junto com a identificação) e regravação após regar
    details = await plant_repo.get_details(saved_plant.id, saved_user.id)
    assert details is not None
    assert details.plant.nickname == "Clotilde"
    assert details.species is not None
    assert details.species.scientific_name == "Monstera deliciosa"

    saved_plant.water(now + timedelta(days=3))
    await plant_repo.save(saved_plant)
    await db_session.commit()
    watered = await plant_repo.get_by_id(saved_plant.id, saved_user.id)
    assert watered is not None
    assert watered.watering_streak.current_count == 1

    # 5. Executar Soft Delete
    deleted_ok = await plant_repo.delete(saved_plant.id, saved_user.id)
    await db_session.commit()
    assert deleted_ok is True

    # 6. Verificar que a planta NÃO é mais retornada no jardim
    fetched_after_delete = await plant_repo.get_by_id(saved_plant.id, saved_user.id)
    assert fetched_after_delete is None

    garden_list_after = await plant_repo.list_by_user(saved_user.id)
    assert len(garden_list_after) == 0

    count_after = await plant_repo.count_by_user(saved_user.id)
    assert count_after == 0
    assert await plant_repo.get_by_identification(identification.id, saved_user.id) is None
