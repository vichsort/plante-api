from dataclasses import dataclass
from src.domain.exceptions import PlantNotFoundError, ForbiddenError
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository

@dataclass(frozen=True)
class DeleteUserPlantInputDTO:
    user_id: int
    user_plant_id: int

class DeleteUserPlantUseCase:
    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        user_repo: IUserRepository
    ):
        self.user_plant_repo = user_plant_repo
        self.user_repo = user_repo

    def execute(self, dto: DeleteUserPlantInputDTO) -> None:
        plant = self.user_plant_repo.get_by_id(dto.user_plant_id)
        if not plant:
            raise PlantNotFoundError(dto.user_plant_id)

        # Só o dono pode deletar
        if plant.user_id != dto.user_id:
            raise ForbiddenError("Você não tem permissão para remover esta planta.")

        # Mutações da Entidade: Remove a planta do agregado do usuário
        user = self.user_repo.get_by_id(dto.user_id)
        user.remove_plant_from_garden(plant)

        # Deleta permanentemente os dados mutáveis do banco
        # (Isso fará um CASCADE no banco para CareSchedule, Streak, etc.)
        self.user_plant_repo.delete(plant)
        
        # O User é salvo para atualizar a contagem do jardim
        self.user_repo.save(user)
        
        # NOTA ARQUITETURAL: 
        # Não chamamos self.storage.delete_image(). 
        # A imagem fica órfã no Bucket para treinar a IA.