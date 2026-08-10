from datetime import UTC, datetime, timedelta

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
from src.domain.value_objects.user_location import UserLocation


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
    await db_session.commit()

    # 2. Criar e salvar planta do usuário
    care = CareSchedule(
        id=1,
        user_plant_id=None,
        care_type=CareType.WATER,
        interval=CareInterval(days=2),
        is_active=True,
        next_due_at=now + timedelta(days=2),
        created_at=now,
    )

    plant = UserPlant(
        id=None,
        user_id=saved_user.id,
        scientific_name="Monstera deliciosa",
        identification_confidence=0.95,
        identification_source=IdentificationSource.CONSENSUS,
        status=IdentificationStatus.IDENTIFIED,
        added_at=now,
        nickname="Clotilde",
        primary_image_url="http://storage.plante.org/img.jpg",
        care_schedule=care,
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

    # 4. Visão resumida do jardim
    view = await plant_repo.get_garden_view_for_user(saved_user.id)
    assert len(view) == 1
    assert view[0]["nickname"] == "Clotilde"

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
