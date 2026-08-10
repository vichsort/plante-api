from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.models.user_model import UserModel
from src.adapters.persistence.repositories.user_repository import UserRepository
from src.domain.entities.user import User
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation


@pytest.mark.asyncio
async def test_user_repository_save_and_get_by_id(db_session: AsyncSession):
    repo = UserRepository(db_session)
    now = datetime.now(UTC)

    user = User.create_new(
        email="real_db@plante.org",
        hashed_password="hashed_secret_password",
        location=UserLocation(country="BR", state="SP"),
        current_time=now,
    )

    saved_user = await repo.save(user)
    await db_session.commit()

    assert saved_user.id is not None
    assert saved_user.email == "real_db@plante.org"

    # Busca por ID no banco real
    fetched_user = await repo.get_by_id(saved_user.id)
    assert fetched_user is not None
    assert fetched_user.id == saved_user.id
    assert fetched_user.email == "real_db@plante.org"
    assert fetched_user.subscription == SubscriptionTier.FREE

@pytest.mark.asyncio
async def test_user_repository_get_by_email(db_session: AsyncSession):
    repo = UserRepository(db_session)
    now = datetime.now(UTC)

    user = User.create_new(
        email="by_email@plante.org",
        hashed_password="hashed_secret_password",
        location=UserLocation(country="BR", state="RJ"),
        current_time=now,
    )

    saved_user = await repo.save(user)
    await db_session.commit()

    fetched = await repo.get_by_email("by_email@plante.org")
    assert fetched is not None
    assert fetched.id == saved_user.id

@pytest.mark.asyncio
async def test_user_repository_soft_delete_filter(db_session: AsyncSession):
    repo = UserRepository(db_session)
    now = datetime.now(UTC)

    user = User.create_new(
        email="deleted@plante.org",
        hashed_password="hashed_secret_password",
        location=UserLocation(country="BR", state="MG"),
        current_time=now,
    )

    saved_user = await repo.save(user)
    await db_session.commit()

    # Aplica soft delete diretamente no model
    model = await db_session.get(UserModel, saved_user.id)
    assert model is not None
    model.deleted_at = datetime.now(UTC)
    await db_session.commit()

    # O repositório DEVE filtrar registros marcados como deleted_at != None
    fetched_by_id = await repo.get_by_id(saved_user.id)
    assert fetched_by_id is None

    fetched_by_email = await repo.get_by_email("deleted@plante.org")
    assert fetched_by_email is None
