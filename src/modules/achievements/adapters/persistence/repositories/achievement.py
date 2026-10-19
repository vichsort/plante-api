from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.achievements.adapters.persistence.mappers.achievement import (
    AchievementMapper,
)
from src.modules.achievements.adapters.persistence.models.achievement import (
    AchievementModel,
)
from src.modules.achievements.domain.ports.achievement_repository import (
    AchievementView,
    IAchievementRepository,
)
from src.shared.domain import UserId


class AchievementRepository(IAchievementRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_achievements_view(self, user_id: UserId) -> list[AchievementView]:
        stmt = (
            select(AchievementModel)
            .where(AchievementModel.user_id == user_id)
            .order_by(AchievementModel.unlocked_at.desc(), AchievementModel.badge_code)
        )
        result = await self._session.execute(stmt)
        return [AchievementMapper.to_view(m) for m in result.scalars().all()]
