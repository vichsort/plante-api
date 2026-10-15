from dataclasses import dataclass

from src.domain.exceptions import UserNotFoundError
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.ids import UserId
from src.domain.value_objects.user_location import UserLocation


@dataclass(frozen=True)
class UpdateLocationFallbackInputDTO:
    user_id: UserId
    country: str
    state: str

class UpdateLocationFallbackUseCase:
    raises = (UserNotFoundError,)

    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    async def execute(self, dto: UpdateLocationFallbackInputDTO) -> None:
        new_location = UserLocation(country=dto.country, state=dto.state)

        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(user_id=dto.user_id)

        user.update_location(new_location)

        await self.user_repo.save(user)