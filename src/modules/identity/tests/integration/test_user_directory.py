from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.identity.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.services.user_directory import UserDirectory
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId, UserNotFoundError


async def test_region_comes_from_the_profile(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        user = await uow.users.save(User.create_new(
            email="region@plante.org", hashed_password="h", location=UserLocation(country="BR", state="RJ"),
            current_time=datetime.now(UTC),
        ))
        await uow.commit()
    directory = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory))

    # Act
    region = await directory.region_of(user.id)

    # Assert. Hoje: o `title()` do `UserLocation` transforma a sigla "RJ" em "Rj" (anotado no todo)
    assert region == UserLocation(country="BR", state="Rj")


async def test_user_without_account_is_not_found(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    directory = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory))

    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await directory.ensure_exists(UserId(uuid4()))
