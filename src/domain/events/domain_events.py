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