from abc import ABC, abstractmethod

class IHealthRawResponseRepository(ABC):
    @abstractmethod
    async def save(self, health_record_id: int, raw_response: dict) -> None:
        """Persiste o raw_response do Kindwise com TTL de 24h."""
        ...

    @abstractmethod
    async def get(self, health_record_id: int) -> dict | None:
        """Retorna o raw_response associado ao health_record_id, ou None se expirado."""
        ...

    @abstractmethod
    async def delete(self, health_record_id: int) -> None:
        """Remove o raw_response após confirmação — libera memória antecipadamente."""
        ...