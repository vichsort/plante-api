from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.schemas.profile import AchievementItemResponse
from src.bootstrap.container import Container
from src.domain.use_cases.list_user_achievements_use_case import (
    ListUserAchievementsInputDTO,
    ListUserAchievementsUseCase,
)
from src.shared.api import ApiResponse, CurrentUserId, error_responses
from src.shared.domain import UnauthorizedError

router = APIRouter(prefix="/profile", tags=["profile"], responses=error_responses(UnauthorizedError))


@router.get("/achievements", status_code=200, response_model=ApiResponse[list[AchievementItemResponse]])
@inject
async def list_achievements(
    use_case: Annotated[
        ListUserAchievementsUseCase,
        Depends(Provide[Container.use_cases.list_user_achievements_use_case]),
    ],
    user_id: CurrentUserId,
) -> ApiResponse[list[AchievementItemResponse]]:
    achievements = await use_case.execute(ListUserAchievementsInputDTO(user_id=user_id))
    return ApiResponse.success([AchievementItemResponse.from_domain(a) for a in achievements])
