from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.deps import get_current_user_id
from src.api.response import ApiResponse
from src.api.schemas.garden import (
    AddPlantToGardenRequest,
    DeleteUserPlantRequest,
    GardenItemResponse,
    WaterPlantResponse,
)
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
from src.infrastructure.container import Container

router = APIRouter(prefix="/garden", tags=["garden"])

@router.post("", status_code=201, response_model=ApiResponse[dict])
@inject
async def add_plant_to_garden(
    body: AddPlantToGardenRequest,
    use_case: AddPlantToGardenUseCase = Depends(Provide[Container.use_cases.add_plant_to_garden_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[dict]:
    await use_case.execute(AddPlantToGardenInputDTO(
        user_id=user_id,
        user_plant_id=body.user_plant_id,
        sample_id=body.sample_id,
    ))
    return ApiResponse.success({"message": "Plant added to garden successfully."})

@router.get("", status_code=200, response_model=ApiResponse[list[GardenItemResponse]])
@inject
async def get_user_garden(
    use_case: GetUserGardenUseCase = Depends(Provide[Container.use_cases.get_user_garden_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[list[GardenItemResponse]]:
    items = await use_case.execute(GetUserGardenInputDTO(user_id=user_id))
    return ApiResponse.success([GardenItemResponse(**item) for item in items])

@router.delete("/{user_plant_id}", status_code=200, response_model=ApiResponse[dict])
@inject
async def delete_user_plant(
    user_plant_id: str,
    body: DeleteUserPlantRequest,
    use_case: DeleteUserPlantUseCase = Depends(Provide[Container.use_cases.delete_user_plant_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[dict]:
    await use_case.execute(DeleteUserPlantInputDTO(
        user_id=user_id,
        user_plant_id=user_plant_id,
        sample_id=body.sample_id,
    ))
    return ApiResponse.success({"message": "Plant removed from garden successfully."})

@router.post("/{user_plant_id}/water", status_code=200, response_model=ApiResponse[WaterPlantResponse])
@inject
async def water_plant(
    user_plant_id: str,
    use_case: WaterPlantUseCase = Depends(Provide[Container.use_cases.water_plant_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[WaterPlantResponse]:
    result = await use_case.execute(WaterPlantInputDTO(
        user_id=user_id,
        user_plant_id=user_plant_id,
    ))
    return ApiResponse.success(WaterPlantResponse(**result))
