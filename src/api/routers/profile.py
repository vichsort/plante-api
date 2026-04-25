from fastapi import APIRouter, Depends
from dependency_injector.wiring import Provide, inject

from src.infrastructure.container import Container
from src.api.deps import get_current_user_id
from src.api.response import ApiResponse
from src.api.schemas.profile import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    UpdateLocationRequest,
    UpgradeSubscriptionRequest,
)
from src.domain.use_cases.change_email_use_case import ChangeEmailUseCase, ChangeEmailInputDTO
from src.domain.use_cases.change_password_use_case import ChangePasswordUseCase, ChangePasswordInputDTO
from src.domain.use_cases.update_location_fallback_use_case import UpdateLocationFallbackUseCase, UpdateLocationFallbackInputDTO
from src.domain.use_cases.upgrade_subscription_use_case import UpgradeSubscriptionUseCase, UpgradeSubscriptionInputDTO
from src.domain.use_cases.list_user_achievements_use_case import ListUserAchievementsUseCase, ListUserAchievementsInputDTO

router = APIRouter(prefix="/profile", tags=["profile"])

@router.patch("/email", status_code=200)
@inject
async def change_email(
    body: ChangeEmailRequest,
    use_case: ChangeEmailUseCase = Depends(Provide[Container.change_email_use_case]),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse:
    await use_case.execute(ChangeEmailInputDTO(
        user_id=user_id,
        current_password=body.current_password,
        new_email=body.new_email,
    ))
    return ApiResponse.ok({"message": "Verification code sent to new email."})

@router.patch("/password", status_code=200)
@inject
async def change_password(
    body: ChangePasswordRequest,
    use_case: ChangePasswordUseCase = Depends(Provide[Container.change_password_use_case]),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse:
    await use_case.execute(ChangePasswordInputDTO(
        user_id=user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    ))
    return ApiResponse.ok({"message": "Password updated successfully."})

@router.patch("/location", status_code=200)
@inject
async def update_location(
    body: UpdateLocationRequest,
    use_case: UpdateLocationFallbackUseCase = Depends(Provide[Container.update_location_fallback_use_case]),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse:
    await use_case.execute(UpdateLocationFallbackInputDTO(
        user_id=user_id,
        country=body.country,
        state=body.state,
    ))
    return ApiResponse.ok({"message": "Location updated successfully."})

@router.post("/subscription/upgrade", status_code=200)
@inject
async def upgrade_subscription(
    body: UpgradeSubscriptionRequest,
    use_case: UpgradeSubscriptionUseCase = Depends(Provide[Container.upgrade_subscription_use_case]),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse:
    result = await use_case.execute(UpgradeSubscriptionInputDTO(
        user_id=user_id,
        plan_duration_days=body.plan_duration_days,
    ))
    return ApiResponse.ok(result)

@router.get("/achievements", status_code=200)
@inject
async def list_achievements(
    use_case: ListUserAchievementsUseCase = Depends(Provide[Container.list_user_achievements_use_case]),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse:
    result = await use_case.execute(ListUserAchievementsInputDTO(user_id=user_id))
    return ApiResponse.ok(result)