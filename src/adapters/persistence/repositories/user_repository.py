from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.domain.entities.user import User
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.adapters.persistence.models.user_model import UserModel
from src.adapters.persistence.mappers.user_mapper import UserMapper

class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> User:
        model = UserMapper.to_model(user)
        self._session.add(model)
        await self._session.flush()  # popula model.id sem fechar transação
        return UserMapper.to_domain(model)

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._session.get(UserModel, user_id)
        return UserMapper.to_domain(result) if result else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return UserMapper.to_domain(model) if model else None

    async def update_fcm_token(self, user_id: int, fcm_token: str) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(fcm_token=fcm_token, fcm_token_updated_at=datetime.now())
        )
        await self._session.execute(stmt)

    async def update_subscription(
        self,
        user_id: int,
        tier: SubscriptionTier,
        expires_at: datetime,
    ) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(subscription=tier.value, subscription_expires_at=expires_at)
        )
        await self._session.execute(stmt)