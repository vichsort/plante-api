from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from datetime import datetime, timezone
from src.domain.ports.achievement_repository import IAchievementRepository
from src.adapters.persistence.models.achievement_model import AchievementModel
from src.adapters.persistence.mappers.achievement_mapper import AchievementMapper

class AchievementRepository(IAchievementRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_achievements_view(self, user_id: int) -> list[dict]:
        stmt = select(AchievementModel).where(AchievementModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return [AchievementMapper.to_dict(m) for m in result.scalars().all()]

    async def grant_badge(self, user_id: int, badge_code: str) -> None:
        model = AchievementModel(
            user_id=user_id,
            badge_code=badge_code,
            unlocked_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.flush()