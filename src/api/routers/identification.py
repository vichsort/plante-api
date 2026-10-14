from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.api.deps import get_current_user_id
from src.api.openapi import error_responses
from src.api.response import ApiResponse
from src.api.schemas.identification import (
    ConfirmPlantIdentificationRequest,
    ConfirmPlantIdentificationResponse,
    IdentifyPlantResponse,
)
from src.domain.exceptions import (
    ExternalServiceError,
    LowConfidenceError,
    PlantLimitExceededError,
    SampleNotFoundError,
    SubscriptionRequiredError,
    UnauthorizedError,
    UserNotFoundError,
)
from src.domain.use_cases.confirm_plant_identification_use_case import (
    ConfirmPlantIdentificationInputDTO,
    ConfirmPlantIdentificationUseCase,
)
from src.domain.use_cases.identify_plant_use_case import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.infrastructure.container import Container

router = APIRouter(prefix="/identify", tags=["identification"], responses=error_responses(UnauthorizedError))

@router.post(
    "",
    status_code=200,
    response_model=ApiResponse[IdentifyPlantResponse],
    responses=error_responses(
        LowConfidenceError,
        UserNotFoundError,
        PlantLimitExceededError,
        SubscriptionRequiredError,
        ExternalServiceError,
    ),
)
@inject
async def identify_plant(
    image: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    use_case: IdentifyPlantUseCase = Depends(Provide[Container.use_cases.identify_plant_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[IdentifyPlantResponse]:
    image_bytes = await image.read()

    result = await use_case.execute(IdentifyPlantInputDTO(
        user_id=user_id,
        image_bytes=image_bytes,
        latitude=latitude,
        longitude=longitude,
    ))

    return ApiResponse.success(IdentifyPlantResponse(**result))

@router.post(
    "/confirm",
    status_code=200,
    response_model=ApiResponse[ConfirmPlantIdentificationResponse],
    responses=error_responses(SampleNotFoundError, UserNotFoundError),
)
@inject
async def confirm_plant_identification(
    body: ConfirmPlantIdentificationRequest,
    use_case: ConfirmPlantIdentificationUseCase = Depends(Provide[Container.use_cases.confirm_plant_identification]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[ConfirmPlantIdentificationResponse]:
    result = await use_case.execute(ConfirmPlantIdentificationInputDTO(
        user_id=user_id,
        sample_id=body.sample_id,
    ))
    return ApiResponse.success(ConfirmPlantIdentificationResponse(**result))