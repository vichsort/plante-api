from dataclasses import dataclass

from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.shared.domain import UserId


@dataclass(frozen=True)
class DeleteUserPlantInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId


class DeleteUserPlantUseCase:
    """
    Tira a planta do jardim (soft delete). Não é rejeição da identificação — a planta pode ter
    morrido ou sido doada — então nem a identificação nem o dado de treino mudam.
    """

    raises = (PlantNotFoundError,)

    def __init__(self, uow: IGardenUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: DeleteUserPlantInputDTO) -> None:
        async with self.uow as uow:
            if not await uow.user_plants.delete(user_plant_id=dto.user_plant_id, user_id=dto.user_id):
                raise PlantNotFoundError(dto.user_plant_id)
            await uow.commit()
