from psycopg.errors import ForeignKeyViolation
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.subscription.adapters.persistence.mappers.subscription import (
    SubscriptionMapper,
)
from src.modules.subscription.adapters.persistence.models.subscription import (
    SubscriptionModel,
)
from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.ports.repository import ISubscriptionRepository
from src.modules.subscription.domain.value_objects.tier import SubscriptionTier
from src.shared.adapters import utcnow
from src.shared.domain import UserId, UserNotFoundError


class SubscriptionRepository(ISubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UserId) -> Subscription | None:
        model = await self._session.get(SubscriptionModel, user_id)
        return SubscriptionMapper.to_domain(model) if model else None

    async def lock(self, user_id: UserId) -> Subscription:
        now = utcnow()
        # Garante a linha (sem corrida entre duas primeiras cobranças) e só então trava
        ensure_row = insert(SubscriptionModel).values(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            tokens_used_today=0,
            created_at=now,
            updated_at=now,
        ).on_conflict_do_nothing(index_elements=[SubscriptionModel.user_id])
        try:
            await self._session.execute(ensure_row)
        except IntegrityError as exc:
            # A única FK da tabela é para `users`
            if isinstance(exc.orig, ForeignKeyViolation):
                raise UserNotFoundError(user_id=user_id) from exc
            raise

        stmt = (
            select(SubscriptionModel)
            .where(SubscriptionModel.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.execute(stmt)).scalar_one()
        return SubscriptionMapper.to_domain(model)

    async def save(self, subscription: Subscription) -> None:
        await self._session.merge(SubscriptionMapper.to_model(subscription))
        await self._session.flush()
