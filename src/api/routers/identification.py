from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.api.schemas.auth import MessageResponse
from src.api.schemas.identification import (
    IdentificationFeedbackRequest,
    IdentifyPlantResponse,
)
from src.bootstrap.container import Container
from src.domain.use_cases.give_identification_feedback_use_case import (
    GiveIdentificationFeedbackInputDTO,
    GiveIdentificationFeedbackUseCase,
)
from src.domain.use_cases.identify_plant_use_case import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.domain.value_objects.ids import IdentificationId
from src.shared.api import ApiResponse, CurrentUserId, error_responses
from src.shared.domain import UnauthorizedError

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
    latitude: Annotated[float | None, Form(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Form(ge=-180, le=180)] = None,
) -> ApiResponse[IdentifyPlantResponse]:
    output = await use_case.execute(IdentifyPlantInputDTO(
        user_id=user_id,
        image_bytes=await image.read(),
        latitude=latitude,
        longitude=longitude,
    ))
    return ApiResponse.success(IdentifyPlantResponse.from_domain(output))


@router.post(
    "/{identification_id}/feedback",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*GiveIdentificationFeedbackUseCase.raises),
)
@inject
async def give_identification_feedback(
    identification_id: UUID,
    body: IdentificationFeedbackRequest,
    use_case: Annotated[
        GiveIdentificationFeedbackUseCase,
        Depends(Provide[Container.use_cases.give_identification_feedback_use_case]),
    ],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    """A identificação acertou, errou ou o usuário não sabe. Pode ser enviado a qualquer momento."""
    await use_case.execute(GiveIdentificationFeedbackInputDTO(
        user_id=user_id,
        identification_id=IdentificationId(identification_id),
        verdict=body.verdict,
        suggested_name=body.suggested_name,
    ))
    return ApiResponse.success(MessageResponse(message="Feedback recorded."))
