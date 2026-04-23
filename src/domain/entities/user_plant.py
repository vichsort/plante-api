from dataclasses import dataclass, field
from datetime import datetime, timezone
from src.domain.value_objects.streak import Streak
from src.domain.exceptions import PlantNotReadyForWateringError
from enum import Enum

class IdentificationStatus(Enum):
    IDENTIFIED = "identified"
    PENDING_ENRICHMENT = "pending_enrichment"
    ENRICHED = "enriched"

@dataclass(frozen=True)
class UserPlant:
    id: int
    user_id: int
    scientific_name: str        # referência à PlantSpecies
    identification_confidence: float
    identification_source: str  # "kindwise" | "plantnet"
    status: IdentificationStatus
    added_at: datetime

    nickname: str | None = None
    primary_image_url: str | None = None
    watering_streak: Streak = field(default_factory=lambda: Streak(current_count=0))
    last_watered_at: datetime | None = None
    next_watering_at: datetime | None = None

    def __post_init__(self):
        if not 0.0 <= self.identification_confidence <= 1.0:
            raise ValueError("identification_confidence needs to be between 0.0 and 1.0.")
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be null.")

    @property
    def display_name(self) -> str:
        """Nome de exibição: apelido do usuário ou nome científico."""
        return self.nickname or self.scientific_name

    @property
    def needs_watering(self) -> bool:
        """Verifica se a planta precisa ser regada hoje pedindo ao cronograma."""
        return self.care_schedule.is_overdue(datetime.now(timezone.utc))

    @property
    def water(self, action_time: datetime) -> None:
        """
        Executa a ação de rega, aplicando validações rigorosas de tempo e gamificação.
        """
        if self.care_schedule.next_due_at and action_time < self.care_schedule.next_due_at:
            raise PlantNotReadyForWateringError(
                next_date=self.care_schedule.next_due_at.strftime("%d/%m/%Y")
            )

        # Atualiza a Ofensiva (Streak)
        self.streak = self.streak.register_action(action_time)

        # Atualiza o Cronograma de Cuidado
        self.care_schedule = self.care_schedule.complete(action_time)

    @property
    def check_and_reset_streak(self, current_time: datetime) -> bool:
        """
        Verifica se a planta passou do prazo de carência para rega.
        Retorna True se o streak foi resetado.
        """
        if self.streak.current_count <= 1:
            return False # Já está no mínimo

        # Se a próxima rega era ONTEM (ou antes) e já passou das 08h de HOJE
        # (A lógica de 'carência' já está embutida no VO Streak via _get_domain_date)
        if self.care_schedule.is_overdue(current_time):
            # Resetamos o Streak VO para um novo começando em 1
            # mas mantendo o last_action_time original para referência
            from src.domain.value_objects.streak import Streak
            self.streak = Streak(current_count=1, last_action_time=self.streak.last_action_time)
            return True
            
        return False