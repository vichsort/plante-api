from dataclasses import dataclass
from src.domain.exceptions import UserNotFoundError
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.user_location import UserLocation

@dataclass(frozen=True)
class UpdateLocationFallbackInputDTO:
    user_id: int
    country: str
    state: str

class UpdateLocationFallbackUseCase:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    async def execute(self, dto: UpdateLocationFallbackInputDTO) -> None:
        # Valida o VO antes de qualquer I/O — falha rápido e barato
        new_location = UserLocation(country=dto.country, state=dto.state)

        # I/O só acontece com dados já validados
        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        # Mutação protegida pela entidade
        user.update_location(new_location)

        await self.user_repo.save(user)