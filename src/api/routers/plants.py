from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.deps import CurrentUserId
from src.api.schemas.plants import PlantDetailsResponse
from src.bootstrap.container import Container
from src.domain.exceptions import UnauthorizedError
from src.domain.use_cases.get_plant_details_use_case import (
    GetPlantDetailsInputDTO,
    GetPlantDetailsUseCase,
)
from src.domain.value_objects.ids import UserPlantId
from src.shared.api import ApiResponse, error_responses

router = APIRouter(prefix="/plants", tags=["plants"], responses=error_responses(UnauthorizedError))


@router.get(
    "/{user_plant_id}",
    status_code=200,
    response_model=ApiResponse[PlantDetailsResponse],
    responses=error_responses(*GetPlantDetailsUseCase.raises),
)
@inject
async def get_plant_details(
    user_plant_id: UUID,
    use_case: Annotated[GetPlantDetailsUseCase, Depends(Provide[Container.use_cases.get_plant_details_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[PlantDetailsResponse]:
    details = await use_case.execute(GetPlantDetailsInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
    ))
    return ApiResponse.success(PlantDetailsResponse.from_domain(details))
