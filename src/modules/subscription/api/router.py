from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.modules.subscription.api.schemas import (
    UpgradeSubscriptionRequest,
    UpgradeSubscriptionResponse,
)
from src.modules.subscription.container import SubscriptionContainer
from src.modules.subscription.domain.use_cases.upgrade_subscription import (
    UpgradeSubscriptionInputDTO,
    UpgradeSubscriptionUseCase,
)
from src.shared.api import ApiResponse, CurrentUserId, error_responses
from src.shared.domain import UnauthorizedError

# Sob `/profile`, a tela "Meu perfil" do cliente (outros módulos também registram rotas ali)
router = APIRouter(prefix="/profile", tags=["profile"], responses=error_responses(UnauthorizedError))


@router.post(
    "/subscription/upgrade",
    status_code=200,
    response_model=ApiResponse[UpgradeSubscriptionResponse],
    responses=error_responses(*UpgradeSubscriptionUseCase.raises),
)
@inject
async def upgrade_subscription(
    body: UpgradeSubscriptionRequest,
    use_case: Annotated[
        UpgradeSubscriptionUseCase,
        Depends(Provide[SubscriptionContainer.upgrade_subscription_use_case]),
    ],
    user_id: CurrentUserId,
) -> ApiResponse[UpgradeSubscriptionResponse]:
    subscription = await use_case.execute(UpgradeSubscriptionInputDTO(
        user_id=user_id,
        plan_duration_days=body.plan_duration_days,
    ))
    return ApiResponse.success(UpgradeSubscriptionResponse.from_domain(subscription))
