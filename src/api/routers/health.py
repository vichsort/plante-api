from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.api.deps import CurrentUserId
from src.api.openapi import error_responses
from src.api.response import ApiResponse
from src.api.schemas.health import (
    ConfirmHealthDiagnosisRequest,
    ConfirmHealthDiagnosisResponse,
    HealthDiagnosisResponse,
    HealthRecordItemResponse,
)
from src.domain.exceptions import UnauthorizedError
from src.domain.use_cases.confirm_health_diagnosis_use_case import (
    ConfirmHealthDiagnosisInputDTO,
    ConfirmHealthDiagnosisUseCase,
)
from src.domain.use_cases.diagnose_health_use_case import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.domain.use_cases.get_health_history_use_case import (
    GetHealthHistoryInputDTO,
    GetHealthHistoryUseCase,
)
from src.domain.value_objects.ids import HealthRecordId, UserPlantId
from src.infrastructure.container import Container

router = APIRouter(prefix="/diagnose", tags=["diagnosis"], responses=error_responses(UnauthorizedError))


@router.post(
    "",
    status_code=200,
    response_model=ApiResponse[HealthDiagnosisResponse],
    responses=error_responses(*DiagnoseHealthUseCase.raises),
)
@inject
async def diagnose_health(
    user_plant_id: Annotated[UUID, Form()],
    image: Annotated[UploadFile, File()],
    use_case: Annotated[DiagnoseHealthUseCase, Depends(Provide[Container.use_cases.diagnose_health_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[HealthDiagnosisResponse]:
    output = await use_case.execute(DiagnoseHealthInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
        image_bytes=await image.read(),
    ))
    return ApiResponse.success(HealthDiagnosisResponse.from_domain(output))


@router.post(
    "/confirm",
    status_code=200,
    response_model=ApiResponse[ConfirmHealthDiagnosisResponse],
    responses=error_responses(*ConfirmHealthDiagnosisUseCase.raises),
)
@inject
async def confirm_health_diagnosis(
    body: ConfirmHealthDiagnosisRequest,
    use_case: Annotated[ConfirmHealthDiagnosisUseCase, Depends(Provide[Container.use_cases.confirm_health_diagnosis])],
    user_id: CurrentUserId,
) -> ApiResponse[ConfirmHealthDiagnosisResponse]:
    sample = await use_case.execute(ConfirmHealthDiagnosisInputDTO(
        user_id=user_id,
        health_record_id=HealthRecordId(body.health_record_id),
    ))
    return ApiResponse.success(ConfirmHealthDiagnosisResponse.from_domain(sample))


@router.get(
    "/history/{user_plant_id}",
    status_code=200,
    response_model=ApiResponse[list[HealthRecordItemResponse]],
    responses=error_responses(*GetHealthHistoryUseCase.raises),
)
@inject
async def get_health_history(
    user_plant_id: UUID,
    use_case: Annotated[GetHealthHistoryUseCase, Depends(Provide[Container.use_cases.get_health_history_use_case])],
    user_id: CurrentUserId,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[list[HealthRecordItemResponse]]:
    records = await use_case.execute(GetHealthHistoryInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
        limit=limit,
    ))
    return ApiResponse.success([HealthRecordItemResponse.from_domain(record) for record in records])
