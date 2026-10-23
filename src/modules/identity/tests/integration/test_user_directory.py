from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.identity.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.exceptions import TermsNotAcceptedError
from src.modules.identity.domain.services.user_directory import UserDirectory
from src.modules.identity.domain.value_objects.terms import Terms
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId, UserNotFoundError

TERMS = Terms(version="2")


async def test_region_comes_from_the_profile(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        user = await uow.users.save(User.create_new(
            email="region@plante.org", hashed_password="h", location=UserLocation(country="BR", state="RJ"),
            current_time=datetime.now(UTC),
        ))
        await uow.commit()
    directory = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory), TERMS)

    # Act
    region = await directory.region_of(user.id)

    # Assert
    assert region == UserLocation(country="BR", state="RJ")


async def test_user_without_account_is_not_found(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    directory = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory), TERMS)

    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await directory.ensure_exists(UserId(uuid4()))


async def test_maintainer_finds_the_user_by_the_email_as_typed(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        user = await uow.users.save(User.create_new(
            email="school@plante.org", hashed_password="h", location=UserLocation(country="BR", state="RJ"),
            current_time=datetime.now(UTC),
        ))
        await uow.commit()
    directory = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory), TERMS)

    # Act
    found = await directory.id_by_email(" School@Plante.org ")

    # Assert
    assert found == user.id


async def test_unknown_email_is_not_found(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    directory = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory), TERMS)

    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await directory.id_by_email("nobody@plante.org")


async def test_only_the_terms_in_force_let_the_photo_out(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange: one account accepted the version in force, the other an older one
    now = datetime.now(UTC)
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        current, outdated = (
            User.create_new(email=f"{name}@plante.org", hashed_password="h", location=UserLocation(country="BR", state="SP"), current_time=now)
            for name in ("current", "outdated")
        )
        current.accept_terms("2", now)
        outdated.accept_terms("1", now)
        await uow.users.save(current)
        await uow.users.save(outdated)
        await uow.commit()
    directory = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory), TERMS)

    # Act & Assert
    await directory.ensure_accepted_terms(current.id)
    with pytest.raises(TermsNotAcceptedError):
        await directory.ensure_accepted_terms(outdated.id)
