from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.exceptions import (
    ForbiddenError,
    PlantNotFoundError,
    SampleNotFoundError,
    UserNotFoundError,
)
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import IdentificationSampleId, UserId, UserPlantId


@dataclass(frozen=True)
class DeleteUserPlantInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    sample_id: IdentificationSampleId

class DeleteUserPlantUseCase:
    raises = (ForbiddenError, PlantNotFoundError, SampleNotFoundError, UserNotFoundError)

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: DeleteUserPlantInputDTO) -> None:
        now = datetime.now(UTC)

        async with self.uow as uow:
            plant = await uow.user_plants.get_by_id(dto.user_plant_id, dto.user_id)
            if plant is None:
                raise PlantNotFoundError(dto.user_plant_id)

            if plant.user_id != dto.user_id:
                raise ForbiddenError("Você não tem permissão para remover esta planta.")

            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            sample = await uow.identification_samples.get_by_id(dto.sample_id)
            if sample is None:
                raise SampleNotFoundError(dto.sample_id)

            user.remove_plant_from_garden()

            await uow.user_plants.delete(user_plant_id=dto.user_plant_id, user_id=dto.user_id)
            await uow.users.save(user)
            await uow.identification_samples.save(sample.reject(rejected_at=now))
            await uow.commit()
