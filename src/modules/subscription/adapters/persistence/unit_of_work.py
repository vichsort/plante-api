from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.subscription.adapters.persistence.repositories.subscription import (
    SubscriptionRepository,
)
from src.modules.subscription.domain.ports.unit_of_work import ISubscriptionUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemySubscriptionUnitOfWork(SqlAlchemyUnitOfWork, ISubscriptionUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.subscriptions = SubscriptionRepository(session)
