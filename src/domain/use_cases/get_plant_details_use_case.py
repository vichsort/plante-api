from dataclasses import dataclass
from src.domain.exceptions import PlantNotFoundError
from src.domain.ports.user_plant_repository import IUserPlantRepository

@dataclass(frozen=True)
class GetPlantDetailsInputDTO:
    user_id: int
    user_plant_id: int

class GetPlantDetailsUseCase:
    def __init__(self, user_plant_repo: IUserPlantRepository):
        self.user_plant_repo = user_plant_repo

    def execute(self, dto: GetPlantDetailsInputDTO) -> dict:
        # Traz um dicionário gordo com JOINs (UserPlant + PlantSpecies + CareSchedule)
        plant_view = self.user_plant_repo.get_plant_details_view(dto.user_plant_id, dto.user_id)
        
        if not plant_view:
            raise PlantNotFoundError(dto.user_plant_id)
            
        return plant_view