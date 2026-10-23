"""A cota de verdade, sobre o Postgres: sem linha = standard; a cobrança trava a linha na transação de quem chama."""
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.quota.adapters.persistence.unit_of_work import (
    SqlAlchemyQuotaUnitOfWork,
)
from src.modules.quota.domain.exceptions import (
    DailyQuotaExceededError,
    PlantLimitExceededError,
)
from src.modules.quota.domain.services.garden_quota import GardenQuota
from src.modules.quota.domain.services.token_wallet import TokenWallet
from src.modules.quota.domain.value_objects.level import FeatureCost
from src.modules.quota.tests.fakes import POLICY
from src.shared.domain import LocalCalendar, UserId, UserNotFoundError

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
CALENDAR = LocalCalendar.from_name("America/Sao_Paulo")
Account = Callable[[], Awaitable[UserId]]


def _uow(factory: async_sessionmaker[AsyncSession]) -> SqlAlchemyQuotaUnitOfWork:
    return SqlAlchemyQuotaUnitOfWork(factory)


async def _charge(factory: async_sessionmaker[AsyncSession], user_id: UserId, cost: FeatureCost) -> None:
    caller = _uow(factory)  # qualquer UoW serve de dono da transação
    async with caller:
        await TokenWallet(_uow(factory), CALENDAR, POLICY).charge(user_id, cost, NOW)
        await caller.commit()


async def test_user_without_a_row_has_the_standard_quota(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    wallet = TokenWallet(_uow(session_factory), CALENDAR, POLICY)

    # Act & Assert: nada gravado, e mesmo assim cabe uma identificação
    await wallet.ensure_can_identify(UserId(uuid4()), NOW)


async def test_charges_add_up_until_the_quota_is_spent(
    session_factory: async_sessionmaker[AsyncSession], account: Account,
) -> None:
    # Arrange
    user_id = await account()
    wallet = TokenWallet(_uow(session_factory), CALENDAR, POLICY)

    # Act
    for _ in range(3):
        await _charge(session_factory, user_id, FeatureCost.IDENTIFY)

    # Assert
    with pytest.raises(DailyQuotaExceededError):
        await wallet.ensure_can_identify(user_id, NOW)


async def test_callers_rollback_takes_the_charge_with_it(
    session_factory: async_sessionmaker[AsyncSession], account: Account,
) -> None:
    # Arrange
    user_id = await account()
    caller = _uow(session_factory)

    # Act: a identificação falhou depois da cobrança; nada pode ficar cobrado
    async with caller:
        await TokenWallet(_uow(session_factory), CALENDAR, POLICY).charge(user_id, FeatureCost.IDENTIFY, NOW)

    # Assert
    async with _uow(session_factory) as uow:
        assert await uow.quotas.get(user_id) is None


async def test_charging_outside_a_transaction_fails_loudly(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    wallet = TokenWallet(_uow(session_factory), CALENDAR, POLICY)

    # Act & Assert: sem dono, ninguém confirmaria a cobrança
    with pytest.raises(RuntimeError, match="inside the caller's unit of work"):
        await wallet.charge(UserId(uuid4()), FeatureCost.IDENTIFY, NOW)


async def test_charging_a_user_without_account_is_not_found(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await _charge(session_factory, UserId(uuid4()), FeatureCost.IDENTIFY)


async def test_garden_quota_follows_the_level(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    quota = GardenQuota(_uow(session_factory), POLICY)
    user_id = UserId(uuid4())

    # Act & Assert: standard (sem linha) até 3
    await quota.ensure_can_add_plant(user_id, plants_in_garden=2, now=NOW)
    with pytest.raises(PlantLimitExceededError):
        await quota.ensure_can_add_plant(user_id, plants_in_garden=3, now=NOW)
