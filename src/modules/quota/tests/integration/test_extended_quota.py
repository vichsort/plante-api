"""The maintainer's grant and revoke, on Postgres."""
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.quota.adapters.persistence.unit_of_work import (
    SqlAlchemyQuotaUnitOfWork,
)
from src.modules.quota.domain.use_cases.grant_extended_quota import (
    GrantExtendedQuotaInputDTO,
    GrantExtendedQuotaUseCase,
)
from src.modules.quota.domain.use_cases.revoke_extended_quota import (
    RevokeExtendedQuotaUseCase,
)
from src.modules.quota.domain.value_objects.level import QuotaLevel
from src.shared.domain import UserId, UserNotFoundError

Account = Callable[[], Awaitable[UserId]]


def _grant(factory: async_sessionmaker[AsyncSession]) -> GrantExtendedQuotaUseCase:
    return GrantExtendedQuotaUseCase(SqlAlchemyQuotaUnitOfWork(factory))


async def _stored(factory: async_sessionmaker[AsyncSession], user_id: UserId) -> tuple[QuotaLevel, datetime | None]:
    async with SqlAlchemyQuotaUnitOfWork(factory) as uow:
        quota = await uow.quotas.get(user_id)
    assert quota is not None
    return quota.level, quota.expires_at


async def test_grant_stores_the_extended_quota_with_a_deadline(
    session_factory: async_sessionmaker[AsyncSession], account: Account,
) -> None:
    # Arrange: a user without a row (never spent tokens)
    user_id = await account()

    # Act
    await _grant(session_factory).execute(GrantExtendedQuotaInputDTO(user_id=user_id, days=90))

    # Assert
    level, expires_at = await _stored(session_factory, user_id)
    assert level is QuotaLevel.EXTENDED
    assert expires_at is not None
    assert abs(expires_at - (datetime.now(UTC) + timedelta(days=90))) < timedelta(minutes=1)


async def test_revoke_brings_the_standard_quota_back(
    session_factory: async_sessionmaker[AsyncSession], account: Account,
) -> None:
    # Arrange
    user_id = await account()
    await _grant(session_factory).execute(GrantExtendedQuotaInputDTO(user_id=user_id, days=30))

    # Act
    await RevokeExtendedQuotaUseCase(SqlAlchemyQuotaUnitOfWork(session_factory)).execute(user_id)

    # Assert
    assert await _stored(session_factory, user_id) == (QuotaLevel.STANDARD, None)


async def test_grant_to_a_user_without_account_is_not_found(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await _grant(session_factory).execute(GrantExtendedQuotaInputDTO(user_id=UserId(uuid4()), days=30))


@pytest.mark.parametrize("days", [0, -5, 366])
async def test_grant_days_are_bounded(session_factory: async_sessionmaker[AsyncSession], days: int) -> None:
    # Act & Assert: before, the public route took any number of days, even negative
    with pytest.raises(ValueError, match="days"):
        await _grant(session_factory).execute(GrantExtendedQuotaInputDTO(user_id=UserId(uuid4()), days=days))
