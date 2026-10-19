"""Conquistas lidas do Postgres real. Nada as concede ainda: as linhas entram com SQL direto."""
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.achievements.adapters.persistence.unit_of_work import (
    SqlAlchemyAchievementsUnitOfWork,
)
from src.shared.domain import UserId

UNLOCKED_AT = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


async def _user_with_badges(
    session_factory: async_sessionmaker[AsyncSession], *badges: str, unlocked_at: list[datetime] | None = None,
) -> tuple[UserId, list[UUID]]:
    user_id = uuid4()
    ids = [uuid4() for _ in badges]
    times = unlocked_at or [UNLOCKED_AT] * len(badges)
    async with session_factory() as session:
        # A tabela de usuários é do identity: o teste só enxerga a API pública dele
        await session.execute(text(
            "INSERT INTO users (id, email, hashed_password, location_country, location_state, is_verified, created_at, updated_at) "
            "VALUES (:id, :email, 'h', 'BR', 'SP', true, now(), now())"
        ), {"id": user_id, "email": f"{user_id}@plante.org"})
        for achievement_id, badge, at in zip(ids, badges, times, strict=True):
            await session.execute(text(
                "INSERT INTO user_achievements (id, user_id, badge_code, unlocked_at, created_at, updated_at) "
                "VALUES (:id, :user_id, :badge, :unlocked_at, now(), now())"
            ), {"id": achievement_id, "user_id": user_id, "badge": badge, "unlocked_at": at})
        await session.commit()
    return UserId(user_id), ids


async def test_lists_only_the_users_achievements(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    user, (first_plant, streak) = await _user_with_badges(session_factory, "first_plant", "streak_1_month")
    await _user_with_badges(session_factory, "ten_plants")

    # Act
    async with SqlAlchemyAchievementsUnitOfWork(session_factory) as uow:
        achievements = await uow.achievements.get_user_achievements_view(user)

    # Assert
    assert sorted((a.id, a.badge_code, a.unlocked_at) for a in achievements) == sorted([
        (first_plant, "first_plant", UNLOCKED_AT),
        (streak, "streak_1_month", UNLOCKED_AT),
    ])


async def test_lists_most_recent_first_with_ties_by_badge_code(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Arrange
    earlier = UNLOCKED_AT - timedelta(days=1)
    user, _ = await _user_with_badges(
        session_factory, "ten_plants", "streak_1_month", "first_plant",
        unlocked_at=[earlier, UNLOCKED_AT, UNLOCKED_AT],
    )

    # Act
    async with SqlAlchemyAchievementsUnitOfWork(session_factory) as uow:
        achievements = await uow.achievements.get_user_achievements_view(user)

    # Assert
    assert [a.badge_code for a in achievements] == ["first_plant", "streak_1_month", "ten_plants"]


async def test_user_without_achievements_gets_an_empty_list(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    user, _ = await _user_with_badges(session_factory)

    # Act
    async with SqlAlchemyAchievementsUnitOfWork(session_factory) as uow:
        achievements = await uow.achievements.get_user_achievements_view(user)

    # Assert
    assert achievements == []
