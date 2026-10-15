from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.deps import CurrentUserId
from src.api.openapi import error_responses
from src.api.response import ApiResponse
from src.api.schemas.auth import MessageResponse
from src.api.schemas.profile import (
    AchievementItemResponse,
    ChangeEmailRequest,
    ChangePasswordRequest,
    UpdateLocationRequest,
    UpgradeSubscriptionRequest,
    UpgradeSubscriptionResponse,
)
from src.domain.exceptions import UnauthorizedError
from src.domain.use_cases.change_email_use_case import (
    ChangeEmailInputDTO,
    ChangeEmailUseCase,
)
from src.domain.use_cases.change_password_use_case import (
    ChangePasswordInputDTO,
    ChangePasswordUseCase,
)
from src.domain.use_cases.list_user_achievements_use_case import (
    ListUserAchievementsInputDTO,
    ListUserAchievementsUseCase,
)
from src.domain.use_cases.update_location_fallback_use_case import (
    UpdateLocationFallbackInputDTO,
    UpdateLocationFallbackUseCase,
)
from src.domain.use_cases.upgrade_subscription_use_case import (
    UpgradeSubscriptionInputDTO,
    UpgradeSubscriptionUseCase,
)
from src.infrastructure.container import Container

router = APIRouter(prefix="/profile", tags=["profile"], responses=error_responses(UnauthorizedError))


@router.patch(
    "/email",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*ChangeEmailUseCase.raises),
)
@inject
async def change_email(
    body: ChangeEmailRequest,
    use_case: Annotated[ChangeEmailUseCase, Depends(Provide[Container.use_cases.change_email_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(ChangeEmailInputDTO(
        user_id=user_id,
        current_password=body.current_password,
        new_email=body.new_email,
    ))
    return ApiResponse.success(MessageResponse(message="Verification code sent to new email."))


@router.patch(
    "/password",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*ChangePasswordUseCase.raises),
)
@inject
async def change_password(
    body: ChangePasswordRequest,
    use_case: Annotated[ChangePasswordUseCase, Depends(Provide[Container.use_cases.change_password_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(ChangePasswordInputDTO(
        user_id=user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    ))
    return ApiResponse.success(MessageResponse(message="Password updated successfully."))


@router.patch(
    "/location",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*UpdateLocationFallbackUseCase.raises),
)
@inject
async def update_location(
    body: UpdateLocationRequest,
    use_case: Annotated[
        UpdateLocationFallbackUseCase,
        Depends(Provide[Container.use_cases.update_location_fallback_use_case]),
    ],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(UpdateLocationFallbackInputDTO(
        user_id=user_id,
        country=body.country,
        state=body.state,
    ))
    return ApiResponse.success(MessageResponse(message="Location updated successfully."))


@router.post(
    "/subscription/upgrade",
    status_code=200,
    response_model=ApiResponse[UpgradeSubscriptionResponse],
    responses=error_responses(*UpgradeSubscriptionUseCase.raises),
)
@inject
async def upgrade_subscription(
    body: UpgradeSubscriptionRequest,
    use_case: Annotated[UpgradeSubscriptionUseCase, Depends(Provide[Container.use_cases.upgrade_subscription_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[UpgradeSubscriptionResponse]:
    user = await use_case.execute(UpgradeSubscriptionInputDTO(
        user_id=user_id,
        plan_duration_days=body.plan_duration_days,
    ))
    return ApiResponse.success(UpgradeSubscriptionResponse.from_domain(user))


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
