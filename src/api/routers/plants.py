from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.deps import get_current_user_id
from src.api.response import ApiResponse
from src.domain.use_cases.get_plant_details_use_case import (
    GetPlantDetailsInputDTO,
    GetPlantDetailsUseCase,
)
from src.infrastructure.container import Container

router = APIRouter(prefix="/plants", tags=["plants"])

@router.get("/{user_plant_id}", status_code=200, response_model=ApiResponse[dict])
@inject
async def get_plant_details(
    user_plant_id: str,
    use_case: GetPlantDetailsUseCase = Depends(Provide[Container.use_cases.get_plant_details_use_case]),
    user_id: Any = Depends(get_current_user_id),
) -> ApiResponse[dict]:
    result = await use_case.execute(GetPlantDetailsInputDTO(
        user_id=user_id,
        user_plant_id=user_plant_id,
    ))
    return ApiResponse.success(result)
