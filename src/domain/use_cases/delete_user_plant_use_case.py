from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.exceptions import (
    ForbiddenError,
    PlantNotFoundError,
    SampleNotFoundError,
    UserNotFoundError,
)
from src.domain.ports.identification_sample_repository import IIdentificationSampleRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository

@dataclass(frozen=True)
class DeleteUserPlantInputDTO:
    user_id: int
    user_plant_id: int
    sample_id: int

class DeleteUserPlantUseCase:
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
        now = datetime.now(timezone.utc)

        plant = await self.user_plant_repo.get_by_id(dto.user_plant_id)
        if plant is None:
            raise PlantNotFoundError(dto.user_plant_id)

        if plant.user_id != dto.user_id:
            raise ForbiddenError("Você não tem permissão para remover esta planta.")

        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        sample = await self.sample_repo.get_by_id(dto.sample_id)
        if sample is None:
            raise SampleNotFoundError(dto.sample_id)

        user.remove_plant_from_garden()
        rejected_sample = sample.reject(rejected_at=now)

        await self.user_plant_repo.delete(plant)
        await self.user_repo.save(user)
        await self.sample_repo.save(rejected_sample)

        # NOTA ARQUITETURAL:
        # Não chamamos storage.delete_image() — imagem permanece no bucket para treino.
        # sample rejeitada é sinal negativo válido para o pipeline de ML.