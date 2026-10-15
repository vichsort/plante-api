from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.domain.exceptions import (
    ForbiddenError,
    PlantNotFoundError,
    SampleNotFoundError,
    UserNotFoundError,
)
from src.domain.ports.identification_sample_repository import (
    IIdentificationSampleRepository,
)
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository


@dataclass(frozen=True)
class DeleteUserPlantInputDTO:
    user_id: Any
    user_plant_id: Any
    sample_id: Any

class DeleteUserPlantUseCase:
    raises = (ForbiddenError, PlantNotFoundError, SampleNotFoundError, UserNotFoundError)

    def __init__(
        self,
        user_repo: IUserRepository,
        user_plant_repo: IUserPlantRepository,
        sample_repo: IIdentificationSampleRepository,
    ) -> None:
        self.user_repo = user_repo
        self.user_plant_repo = user_plant_repo
        self.sample_repo = sample_repo

    async def execute(self, dto: DeleteUserPlantInputDTO) -> None:
        now = datetime.now(UTC)

        plant = await self.user_plant_repo.get_by_id(dto.user_plant_id, dto.user_id)
        if plant is None:
            raise PlantNotFoundError(dto.user_plant_id)

        if str(plant.user_id) != str(dto.user_id):
            raise ForbiddenError("Você não tem permissão para remover esta planta.")

        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(user_id=dto.user_id)

        sample = await self.sample_repo.get_by_id(dto.sample_id)
        if sample is None:
            raise SampleNotFoundError(dto.sample_id)

        user.remove_plant_from_garden()
        rejected_sample = sample.reject(rejected_at=now)

        await self.user_plant_repo.delete(user_plant_id=dto.user_plant_id, user_id=dto.user_id)
        await self.user_repo.save(user)
        await self.sample_repo.save(rejected_sample)