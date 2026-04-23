from dataclasses import dataclass
from src.domain.exceptions import UserNotFoundError
from src.domain.ports.user_repository import IUserRepository

@dataclass(frozen=True)
class UpdateLocationFallbackInputDTO:
    user_id: int
    country: str
    state: str

class UpdateLocationFallbackUseCase:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    def execute(self, dto: UpdateLocationFallbackInputDTO) -> dict:
        user = self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)

        # Mutação protegida pela Entidade (Se for inválido, lança ValueError)
        user.update_location(country=dto.country, state=dto.state)

        self.user_repo.save(user)

        return {
            "message": "Localização atualizada com sucesso.",
            "country": user.country,
            "state": user.state
        }