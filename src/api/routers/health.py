from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.api.deps import get_current_user_id
from src.api.response import ApiResponse
from src.api.schemas.health import (
    ConfirmHealthDiagnosisRequest,
    ConfirmHealthDiagnosisResponse,
    HealthDiagnosisResponse,
    HealthRecordItemResponse,
)
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
from src.infrastructure.container import Container

router = APIRouter(prefix="/diagnose", tags=["diagnosis"])

@router.post("", status_code=200, response_model=ApiResponse[HealthDiagnosisResponse])
@inject
async def diagnose_health(
    user_plant_id: str = Form(...),
    image: UploadFile = File(...),
    use_case: DiagnoseHealthUseCase = Depends(Provide[Container.use_cases.diagnose_health_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[HealthDiagnosisResponse]:
    image_bytes = await image.read()
    result = await use_case.execute(DiagnoseHealthInputDTO(
        user_id=user_id,
        user_plant_id=user_plant_id,
        image_bytes=image_bytes,
    ))
    return ApiResponse.success(HealthDiagnosisResponse(**result))

@router.post("/confirm", status_code=200, response_model=ApiResponse[ConfirmHealthDiagnosisResponse])
@inject
async def confirm_health_diagnosis(
    body: ConfirmHealthDiagnosisRequest,
    use_case: ConfirmHealthDiagnosisUseCase = Depends(Provide[Container.use_cases.confirm_health_diagnosis]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[ConfirmHealthDiagnosisResponse]:
    result = await use_case.execute(ConfirmHealthDiagnosisInputDTO(
        user_id=user_id,
        health_record_id=body.health_record_id,
    ))
    return ApiResponse.success(ConfirmHealthDiagnosisResponse(**result))

@router.get("/history/{user_plant_id}", status_code=200, response_model=ApiResponse[list[HealthRecordItemResponse]])
@inject
async def get_health_history(
    user_plant_id: str,
    limit: int = Query(20, ge=1, le=100),
    use_case: GetHealthHistoryUseCase = Depends(Provide[Container.use_cases.get_health_history_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[list[HealthRecordItemResponse]]:
    records = await use_case.execute(GetHealthHistoryInputDTO(
        user_id=user_id,
        user_plant_id=user_plant_id,
        limit=limit,
    ))
    return ApiResponse.success([HealthRecordItemResponse(**r) for r in records])
