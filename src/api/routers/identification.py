from fastapi import APIRouter, Depends, UploadFile, File, Form
from dependency_injector.wiring import Provide, inject
from src.infrastructure.container import Container
from src.api.deps import get_current_user_id
from src.api.response import ApiResponse
from src.api.schemas.identification import IdentifyPlantResponse
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantUseCase, IdentifyPlantInputDTO

router = APIRouter(prefix="/identify", tags=["identification"])

@router.post("", status_code=200)
@inject
async def identify_plant(
    image: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    use_case: IdentifyPlantUseCase = Depends(Provide[Container.use_cases.provided.identify_plant_use_case]),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse:
    image_bytes = await image.read()

    result = await use_case.execute(IdentifyPlantInputDTO(
        user_id=user_id,
        image_bytes=image_bytes,
        latitude=latitude,
        longitude=longitude,
    ))

    return ApiResponse.ok(IdentifyPlantResponse(**result))