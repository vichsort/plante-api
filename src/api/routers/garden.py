from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.deps import CurrentUserId
from src.api.openapi import error_responses
from src.api.response import ApiResponse
from src.api.schemas.auth import MessageResponse
from src.api.schemas.garden import (
    AddPlantToGardenRequest,
    GardenItemResponse,
    WaterPlantResponse,
)
from src.domain.exceptions import UnauthorizedError
from src.domain.use_cases.add_plant_to_garden_use_case import (
    AddPlantToGardenInputDTO,
    AddPlantToGardenUseCase,
)
from src.domain.use_cases.delete_user_plant_use_case import (
    DeleteUserPlantInputDTO,
    DeleteUserPlantUseCase,
)
from src.domain.use_cases.get_user_garden_use_case import (
    GetUserGardenInputDTO,
    GetUserGardenUseCase,
)
from src.domain.use_cases.water_plant_use_case import (
    WaterPlantInputDTO,
    WaterPlantUseCase,
)
from src.domain.value_objects.ids import IdentificationId, UserPlantId
from src.infrastructure.container import Container

router = APIRouter(prefix="/garden", tags=["garden"], responses=error_responses(UnauthorizedError))


@router.post(
    "",
    status_code=201,
    response_model=ApiResponse[GardenItemResponse],
    responses=error_responses(*AddPlantToGardenUseCase.raises),
)
@inject
async def add_plant_to_garden(
    body: AddPlantToGardenRequest,
    use_case: Annotated[AddPlantToGardenUseCase, Depends(Provide[Container.use_cases.add_plant_to_garden_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[GardenItemResponse]:
    """Cria a planta no jardim a partir de uma identificação. Repetir devolve a mesma planta."""
    plant = await use_case.execute(AddPlantToGardenInputDTO(
        user_id=user_id,
        identification_id=IdentificationId(body.identification_id),
        nickname=body.nickname,
    ))
    return ApiResponse.success(GardenItemResponse.from_domain(plant))


@router.get("", status_code=200, response_model=ApiResponse[list[GardenItemResponse]])
@inject
async def get_user_garden(
    use_case: Annotated[GetUserGardenUseCase, Depends(Provide[Container.use_cases.get_user_garden_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[list[GardenItemResponse]]:
    plants = await use_case.execute(GetUserGardenInputDTO(user_id=user_id))
    return ApiResponse.success([GardenItemResponse.from_domain(plant) for plant in plants])


@router.delete(
    "/{user_plant_id}",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*DeleteUserPlantUseCase.raises),
)
@inject
async def delete_user_plant(
    user_plant_id: UUID,
    use_case: Annotated[DeleteUserPlantUseCase, Depends(Provide[Container.use_cases.delete_user_plant_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(DeleteUserPlantInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
    ))
    return ApiResponse.success(MessageResponse(message="Plant removed from garden successfully."))


@router.post(
    "/{user_plant_id}/water",
    status_code=200,
    response_model=ApiResponse[WaterPlantResponse],
    responses=error_responses(*WaterPlantUseCase.raises),
)
@inject
async def water_plant(
    user_plant_id: UUID,
    use_case: Annotated[WaterPlantUseCase, Depends(Provide[Container.use_cases.water_plant_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[WaterPlantResponse]:
    plant = await use_case.execute(WaterPlantInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
    ))
    return ApiResponse.success(WaterPlantResponse.from_domain(plant))
