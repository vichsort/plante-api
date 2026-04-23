from datetime import datetime, timezone
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.events.domain_events import StreakBrokenEvent

class BreakStreaksCronUseCase:
    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        publisher: IDomainPublisher
    ):
        self.user_plant_repo = user_plant_repo
        self.publisher = publisher

    def execute(self) -> dict:
        """
        Varre plantas atrasadas e reseta ofensivas. 
        Idealmente executado logo após o fim da carência (ex: 08:01 AM).
        """
        now = datetime.now(timezone.utc)
        
        # O repositório deve implementar uma busca eficiente por plantas atrasadas
        # que ainda possuem streak > 1.
        overdue_plants = self.user_plant_repo.find_plants_with_overdue_streaks(now)
        
        counts = {"processed": 0, "broken": 0}

        for plant in overdue_plants:
            counts["processed"] += 1
            
            # Guardamos o valor antigo para o evento
            old_streak = plant.streak.current_count
            
            # Regra de negócio na Entidade: resetar se estiver atrasado
            # A Entidade UserPlant decide se deve resetar com base no tempo atual
            if plant.check_and_reset_streak(now):
                counts["broken"] += 1
                self.user_plant_repo.save(plant)
                
                # Dispara notificação para tentar recuperar o usuário
                event = StreakBrokenEvent.create(
                    user_id=plant.user_id,
                    user_plant_id=plant.id,
                    last_count=old_streak
                )
                self.publisher.publish(event)

        return counts