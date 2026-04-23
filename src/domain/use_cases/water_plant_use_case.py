from dataclasses import dataclass
from datetime import datetime, timezone
from src.domain.exceptions import PlantNotFoundError, ForbiddenError
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.events.domain_events import PlantWateredEvent

@dataclass(frozen=True)
class WaterPlantInputDTO:
    user_id: int
    user_plant_id: int

class WaterPlantUseCase:
    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        publisher: IDomainPublisher
    ):
        self.user_plant_repo = user_plant_repo
        self.publisher = publisher

    def execute(self, dto: WaterPlantInputDTO) -> dict:
        plant = self.user_plant_repo.get_by_id(dto.user_plant_id)
        if not plant:
            raise PlantNotFoundError(dto.user_plant_id)

        # Garante que o usuário não está regando a planta do vizinho
        if plant.user_id != dto.user_id:
            raise ForbiddenError("Você não tem permissão para regar esta planta.")

        # Regra de Negócio: Delega a rega para a Entidade
        # Pega a hora exata do servidor em UTC
        now_utc = datetime.now(timezone.utc)
        
        # Se for cedo demais, a Entidade lança o PlantNotReadyForWateringError
        plant.water(now_utc)

        # Salva a planta atualizada
        self.user_plant_repo.save(plant)

        # Publica o evento (Para o Listener de Conquistas checar se bateu 1 mês de streak, etc)
        event = PlantWateredEvent.create(
            user_id=dto.user_id,
            user_plant_id=plant.id,
            current_streak=plant.streak.current_count
        )
        self.publisher.publish(event)

        # Retorna os dados para a UI atualizar o botão e a ofensiva
        return {
            "user_plant_id": plant.id,
            "last_watered_date": plant.last_watered_date.isoformat(),
            "next_due_date": plant.next_due_date.isoformat(),
            "current_streak": plant.streak.current_count
        }