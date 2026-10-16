from dataclasses import dataclass

from src.domain.exceptions import UserNotFoundError
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId


@dataclass(frozen=True)
class UpdateLocationFallbackInputDTO:
    user_id: UserId
    country: str
    state: str

class UpdateLocationFallbackUseCase:
    raises = (UserNotFoundError,)

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: UpdateLocationFallbackInputDTO) -> None:
        new_location = UserLocation(country=dto.country, state=dto.state)

        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            user.update_location(new_location)
            await uow.users.save(user)
            await uow.commit()
