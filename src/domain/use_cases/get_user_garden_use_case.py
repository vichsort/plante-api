from dataclasses import dataclass
from src.domain.ports.user_plant_repository import IUserPlantRepository

@dataclass(frozen=True)
class GetUserGardenInputDTO:
    user_id: int

class GetUserGardenUseCase:
    def __init__(self, user_plant_repo: IUserPlantRepository):
        self.user_plant_repo = user_plant_repo

    def execute(self, dto: GetUserGardenInputDTO) -> list[dict]:
        # O repositório vai fazer um SELECT otimizado no banco (SQLAlchemy)
        # e devolver algo como: [{"id": 1, "nickname": "Clotilde", "image_url": "...", "needs_watering": True}]
        return self.user_plant_repo.get_garden_view_for_user(dto.user_id)