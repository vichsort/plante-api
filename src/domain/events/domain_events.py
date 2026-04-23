from dataclasses import dataclass
from datetime import datetime, timezone
from abc import ABC

@dataclass(frozen=True)
class DomainEvent(ABC):
    """Classe base para todos os eventos do domínio."""
    occurred_on: datetime

@dataclass(frozen=True)
class PlantIdentifiedEvent(DomainEvent):
    """
    Emitido quando um usuário identifica com sucesso uma planta.
    É um 'Evento Gordo' para poupar consultas futuras ao banco.
    """
    user_id: int
    species_id: int
    is_first_plant: bool
    
    @classmethod
    def create(cls, user_id: int, species_id: int, is_first_plant: bool) -> 'PlantIdentifiedEvent':
        return cls(
            occurred_on=datetime.now(timezone.utc),
            user_id=user_id,
            species_id=species_id,
            is_first_plant=is_first_plant
        )

@dataclass(frozen=True)
class StreakBrokenEvent(DomainEvent):
    """
    Emitido quando um usuário perde a ofensiva de uma planta.
    Útil para disparar Push Notifications de 'recuperação'.
    """
    user_id: int
    user_plant_id: int
    last_streak_count: int

    @classmethod
    def create(cls, user_id: int, user_plant_id: int, last_count: int) -> 'StreakBrokenEvent':
        return cls(
            occurred_on=datetime.now(timezone.utc),
            user_id=user_id,
            user_plant_id=user_plant_id,
            last_streak_count=last_count
        )