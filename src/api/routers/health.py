from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.api.schemas.auth import MessageResponse
from src.api.schemas.health import (
    HealthDiagnosisResponse,
    HealthFeedbackRequest,
    HealthRecordItemResponse,
)
from src.bootstrap.container import Container
from src.domain.use_cases.diagnose_health_use_case import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.domain.use_cases.get_health_history_use_case import (
    GetHealthHistoryInputDTO,
    GetHealthHistoryUseCase,
)
from src.domain.use_cases.give_health_feedback_use_case import (
    GiveHealthFeedbackInputDTO,
    GiveHealthFeedbackUseCase,
)
from src.domain.value_objects.ids import HealthRecordId, UserPlantId
from src.shared.api import ApiResponse, CurrentUserId, error_responses
from src.shared.domain import UnauthorizedError

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
    latitude: Annotated[float | None, Form(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Form(ge=-180, le=180)] = None,
) -> ApiResponse[HealthDiagnosisResponse]:
    output = await use_case.execute(DiagnoseHealthInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
        image_bytes=await image.read(),
        latitude=latitude,
        longitude=longitude,
    ))
    return ApiResponse.success(HealthDiagnosisResponse.from_domain(output))


@router.post(
    "/{health_record_id}/feedback",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*GiveHealthFeedbackUseCase.raises),
)
@inject
async def give_health_feedback(
    health_record_id: UUID,
    body: HealthFeedbackRequest,
    use_case: Annotated[GiveHealthFeedbackUseCase, Depends(Provide[Container.use_cases.give_health_feedback_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    """O diagnóstico acertou, errou ou o usuário não sabe. Pode ser enviado a qualquer momento."""
    await use_case.execute(GiveHealthFeedbackInputDTO(
        user_id=user_id,
        health_record_id=HealthRecordId(health_record_id),
        verdict=body.verdict,
    ))
    return ApiResponse.success(MessageResponse(message="Feedback recorded."))


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
