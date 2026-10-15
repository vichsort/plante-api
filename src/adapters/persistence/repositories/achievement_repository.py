from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.mappers.achievement_mapper import AchievementMapper
from src.adapters.persistence.models.achievement_model import AchievementModel
from src.domain.ports.achievement_repository import (
    AchievementView,
    IAchievementRepository,
)
from src.domain.value_objects.ids import UserId


class AchievementRepository(IAchievementRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_achievements_view(self, user_id: UserId) -> list[AchievementView]:
        stmt = select(AchievementModel).where(AchievementModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return [AchievementMapper.to_view(m) for m in result.scalars().all()]

    async def grant_badge(self, user_id: UserId, badge_code: str) -> None:
        model = AchievementModel(
            user_id=user_id,
            badge_code=badge_code,
            unlocked_at=datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()