from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from src.modules.garden.api.schemas import (
    AddPlantToGardenRequest,
    GardenItemResponse,
    PlantDetailsResponse,
    WaterPlantResponse,
)
from src.modules.garden.container import GardenContainer
from src.modules.garden.domain.use_cases.add_plant import (
    AddPlantToGardenInputDTO,
    AddPlantToGardenUseCase,
)
from src.modules.garden.domain.use_cases.delete_plant import (
    DeleteUserPlantInputDTO,
    DeleteUserPlantUseCase,
)
from src.modules.garden.domain.use_cases.get_garden import (
    GetUserGardenInputDTO,
    GetUserGardenUseCase,
)
from src.modules.garden.domain.use_cases.get_plant_details import (
    GetPlantDetailsInputDTO,
    GetPlantDetailsUseCase,
)
from src.modules.garden.domain.use_cases.water_plant import (
    WaterPlantInputDTO,
    WaterPlantUseCase,
)
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.modules.garden.domain.value_objects.removal_reason import RemovalReason
from src.modules.identification import IdentificationId
from src.shared.api import ApiResponse, CurrentUserId, MessageResponse, error_responses
from src.shared.domain import UnauthorizedError

garden_router = APIRouter(prefix="/garden", tags=["garden"], responses=error_responses(UnauthorizedError))


@garden_router.post(
    "",
    status_code=201,
    response_model=ApiResponse[GardenItemResponse],
    responses=error_responses(*AddPlantToGardenUseCase.raises),
)
@inject
async def add_plant_to_garden(
    body: AddPlantToGardenRequest,
    use_case: Annotated[AddPlantToGardenUseCase, Depends(Provide[GardenContainer.add_plant_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[GardenItemResponse]:
    """Cria a planta no jardim a partir de uma identificação. Repetir devolve a mesma planta."""
    item = await use_case.execute(AddPlantToGardenInputDTO(
        user_id=user_id,
        identification_id=IdentificationId(body.identification_id),
        nickname=body.nickname,
    ))
    return ApiResponse.success(GardenItemResponse.from_domain(item))


@garden_router.get("", status_code=200, response_model=ApiResponse[list[GardenItemResponse]])
@inject
async def get_user_garden(
    use_case: Annotated[GetUserGardenUseCase, Depends(Provide[GardenContainer.get_garden_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[list[GardenItemResponse]]:
    items = await use_case.execute(GetUserGardenInputDTO(user_id=user_id))
    return ApiResponse.success([GardenItemResponse.from_domain(item) for item in items])


@garden_router.delete(
    "/{user_plant_id}",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*DeleteUserPlantUseCase.raises),
)
@inject
async def delete_user_plant(
    user_plant_id: UUID,
    use_case: Annotated[DeleteUserPlantUseCase, Depends(Provide[GardenContainer.delete_plant_use_case])],
    user_id: CurrentUserId,
    reason: Annotated[
        RemovalReason | None,
        Query(description="Why the plant left the garden. `misidentified` tells us the species was wrong."),
    ] = None,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(DeleteUserPlantInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
        reason=reason,
    ))
    return ApiResponse.success(MessageResponse(message="Plant removed from garden successfully."))


@garden_router.post(
    "/{user_plant_id}/water",
    status_code=200,
    response_model=ApiResponse[WaterPlantResponse],
    responses=error_responses(*WaterPlantUseCase.raises),
)
@inject
async def water_plant(
    user_plant_id: UUID,
    use_case: Annotated[WaterPlantUseCase, Depends(Provide[GardenContainer.water_plant_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[WaterPlantResponse]:
    plant = await use_case.execute(WaterPlantInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
    ))
    return ApiResponse.success(WaterPlantResponse.from_domain(plant))


plants_router = APIRouter(prefix="/plants", tags=["plants"], responses=error_responses(UnauthorizedError))


@plants_router.get(
    "/{user_plant_id}",
    status_code=200,
    response_model=ApiResponse[PlantDetailsResponse],
    responses=error_responses(*GetPlantDetailsUseCase.raises),
)
@inject
async def get_plant_details(
    user_plant_id: UUID,
    use_case: Annotated[GetPlantDetailsUseCase, Depends(Provide[GardenContainer.get_plant_details_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[PlantDetailsResponse]:
    details = await use_case.execute(GetPlantDetailsInputDTO(
        user_id=user_id,
        user_plant_id=UserPlantId(user_plant_id),
    ))
    return ApiResponse.success(PlantDetailsResponse.from_domain(details))


# O jardim (`/garden`) e o detalhe de uma planta (`/plants`), nessa ordem (a do OpenAPI)
router = APIRouter()
router.include_router(garden_router)
router.include_router(plants_router)
