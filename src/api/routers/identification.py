from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.api.deps import CurrentUserId
from src.api.openapi import error_responses
from src.api.response import ApiResponse
from src.api.schemas.identification import (
    ConfirmPlantIdentificationRequest,
    ConfirmPlantIdentificationResponse,
    IdentifyPlantResponse,
)
from src.domain.exceptions import UnauthorizedError
from src.domain.use_cases.confirm_plant_identification_use_case import (
    ConfirmPlantIdentificationInputDTO,
    ConfirmPlantIdentificationUseCase,
)
from src.domain.use_cases.identify_plant_use_case import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.domain.value_objects.ids import IdentificationSampleId
from src.infrastructure.container import Container

router = APIRouter(prefix="/identify", tags=["identification"], responses=error_responses(UnauthorizedError))


@router.post(
    "",
    status_code=200,
    response_model=ApiResponse[IdentifyPlantResponse],
    responses=error_responses(*IdentifyPlantUseCase.raises),
)
@inject
async def identify_plant(
    image: Annotated[UploadFile, File()],
    use_case: Annotated[IdentifyPlantUseCase, Depends(Provide[Container.use_cases.identify_plant_use_case])],
    user_id: CurrentUserId,
    latitude: Annotated[float | None, Form()] = None,
    longitude: Annotated[float | None, Form()] = None,
) -> ApiResponse[IdentifyPlantResponse]:
    output = await use_case.execute(IdentifyPlantInputDTO(
        user_id=user_id,
        image_bytes=await image.read(),
        latitude=latitude,
        longitude=longitude,
    ))
    return ApiResponse.success(IdentifyPlantResponse.from_domain(output))


@router.post(
    "/confirm",
    status_code=200,
    response_model=ApiResponse[ConfirmPlantIdentificationResponse],
    responses=error_responses(*ConfirmPlantIdentificationUseCase.raises),
)
@inject
async def confirm_plant_identification(
    body: ConfirmPlantIdentificationRequest,
    use_case: Annotated[
        ConfirmPlantIdentificationUseCase,
        Depends(Provide[Container.use_cases.confirm_plant_identification]),
    ],
    user_id: CurrentUserId,
) -> ApiResponse[ConfirmPlantIdentificationResponse]:
    sample = await use_case.execute(ConfirmPlantIdentificationInputDTO(
        user_id=user_id,
        sample_id=IdentificationSampleId(body.sample_id),
    ))
    return ApiResponse.success(ConfirmPlantIdentificationResponse.from_domain(sample))
