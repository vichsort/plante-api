from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.subscription.adapters.persistence.unit_of_work import (
    SqlAlchemySubscriptionUnitOfWork,
)
from src.modules.subscription.domain.events import SubscriptionUpgradedEvent
from src.modules.subscription.domain.use_cases.upgrade_subscription import (
    UpgradeSubscriptionInputDTO,
    UpgradeSubscriptionUseCase,
)
from src.modules.subscription.domain.value_objects.tier import SubscriptionTier
from src.shared.domain import UserId, UserNotFoundError


async def test_upgrade_stores_pro_and_publishes_the_event(
    session_factory: async_sessionmaker[AsyncSession], account: Callable[[], Awaitable[UserId]],
) -> None:
    # Arrange
    user_id = await account()
    publisher = AsyncMock()
    use_case = UpgradeSubscriptionUseCase(SqlAlchemySubscriptionUnitOfWork(session_factory), publisher)

    # Act
    subscription = await use_case.execute(UpgradeSubscriptionInputDTO(user_id=user_id, plan_duration_days=30))

    # Assert
    async with SqlAlchemySubscriptionUnitOfWork(session_factory) as uow:
        stored = await uow.subscriptions.get(user_id)
    assert stored is not None and stored.tier == SubscriptionTier.PRO
    assert stored.expires_at == subscription.expires_at
    [event] = [call.args[0] for call in publisher.publish.call_args_list]
    assert isinstance(event, SubscriptionUpgradedEvent) and event.plan_name == "PRO"


async def test_upgrade_of_a_user_without_account_is_not_found(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    publisher = AsyncMock()
    use_case = UpgradeSubscriptionUseCase(SqlAlchemySubscriptionUnitOfWork(session_factory), publisher)

    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await use_case.execute(UpgradeSubscriptionInputDTO(user_id=UserId(uuid4()), plan_duration_days=30))
    publisher.publish.assert_not_called()
