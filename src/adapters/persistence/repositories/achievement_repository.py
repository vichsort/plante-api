from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from src.domain.ports.achievement_repository import IAchievementRepository

class AchievementRepository(IAchievementRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_achievements_view(self, user_id: int) -> list[dict]:
        from sqlalchemy import text
        result = await self._session.execute(
            text("SELECT badge_code, unlocked_at FROM user_achievements WHERE user_id = :uid"),
            {"uid": user_id},
        )
        return [{"badge_code": r.badge_code, "unlocked_at": r.unlocked_at} for r in result]

    async def grant_badge(self, user_id: int, badge_code: str) -> None:
        from sqlalchemy import text
        await self._session.execute(
            text("INSERT INTO user_achievements (user_id, badge_code, unlocked_at) VALUES (:uid, :code, :now) ON CONFLICT DO NOTHING"),
            {"uid": user_id, "code": badge_code, "now": datetime.now(timezone.utc)},
        )