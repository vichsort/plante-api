from uuid import uuid4

from src.modules.achievements.domain.use_cases.list_achievements import (
    ListUserAchievementsInputDTO,
    ListUserAchievementsUseCase,
)
from src.modules.achievements.tests.fakes import (
    FakeAchievementsUnitOfWork,
    InMemoryAchievementRepository,
    make_achievement,
)
from src.shared.domain import UserId


async def test_lists_only_the_users_achievements_without_writing() -> None:
    # Arrange
    user, other = UserId(uuid4()), UserId(uuid4())
    mine = make_achievement("first_plant")
    uow = FakeAchievementsUnitOfWork(InMemoryAchievementRepository({user: [mine], other: [make_achievement("ten_plants")]}))

    # Act
    achievements = await ListUserAchievementsUseCase(uow).execute(ListUserAchievementsInputDTO(user_id=user))

    # Assert
    assert achievements == [mine]
    assert (uow.opened, uow.commits) == (1, 0)


async def test_user_without_achievements_gets_an_empty_list() -> None:
    # Arrange
    uow = FakeAchievementsUnitOfWork()

    # Act
    achievements = await ListUserAchievementsUseCase(uow).execute(ListUserAchievementsInputDTO(user_id=UserId(uuid4())))

    # Assert
    assert achievements == []
