from psycopg.errors import ForeignKeyViolation
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.quota.adapters.persistence.mappers.quota import (
    QuotaMapper,
)
from src.modules.quota.adapters.persistence.models.quota import (
    QuotaModel,
)
from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.ports.repository import IQuotaRepository
from src.modules.quota.domain.value_objects.tier import SubscriptionTier
from src.shared.adapters import utcnow
from src.shared.domain import UserId, UserNotFoundError


class QuotaRepository(IQuotaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UserId) -> Quota | None:
        model = await self._session.get(QuotaModel, user_id)
        return QuotaMapper.to_domain(model) if model else None

    async def lock(self, user_id: UserId) -> Quota:
        now = utcnow()
        # Garante a linha (sem corrida entre duas primeiras cobranças) e só então trava
        ensure_row = insert(QuotaModel).values(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            tokens_used_today=0,
            created_at=now,
            updated_at=now,
        ).on_conflict_do_nothing(index_elements=[QuotaModel.user_id])
        try:
            await self._session.execute(ensure_row)
        except IntegrityError as exc:
            # A única FK da tabela é para `users`
            if isinstance(exc.orig, ForeignKeyViolation):
                raise UserNotFoundError(user_id=user_id) from exc
            raise

        stmt = (
            select(QuotaModel)
            .where(QuotaModel.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.execute(stmt)).scalar_one()
        return QuotaMapper.to_domain(model)

    async def save(self, quota: Quota) -> None:
        await self._session.merge(QuotaMapper.to_model(quota))
        await self._session.flush()
