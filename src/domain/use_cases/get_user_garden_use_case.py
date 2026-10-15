from dataclasses import dataclass

from src.domain.entities.user_plant import UserPlant
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import UserId


@dataclass(frozen=True)
class GetUserGardenInputDTO:
    user_id: UserId

class GetUserGardenUseCase:
    raises = ()

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: GetUserGardenInputDTO) -> list[UserPlant]:
        async with self.uow as uow:
            return await uow.user_plants.list_by_user(dto.user_id)
