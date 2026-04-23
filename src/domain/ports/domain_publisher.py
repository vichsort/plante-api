from abc import ABC, abstractmethod
from src.domain.events.domain_events import DomainEvent

class IDomainPublisher(ABC):
    """
    Porta de saída (Megafone) para emissão de eventos.
    O domínio não sabe se isso vai para o Celery, Redis ou Memória.
    """
    
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publica um evento para ser consumido pelos listeners interessados."""
        ...