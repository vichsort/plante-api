from abc import ABC
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base de todos os eventos de domínio. Os eventos concretos moram em `domain/events.py` de cada módulo."""
    occurred_on: datetime
