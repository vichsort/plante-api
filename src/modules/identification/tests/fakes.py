"""
Dublês do identification: `FakeIdentificationLookup` para quem usa o módulo (o garden, hoje código
antigo) e, para os testes daqui, as portas em memória.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import uuid4

from src.modules.catalog import PlantSpeciesId
from src.modules.identification.domain.entities.identification import Identification
from src.modules.identification.domain.exceptions import IdentificationNotFoundError
from src.modules.identification.domain.ports.identification_repository import (
    IIdentificationRepository,
)
from src.modules.identification.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
)
from src.modules.identification.domain.ports.unit_of_work import (
    IIdentificationUnitOfWork,
)
from src.modules.identification.domain.services.identification_lookup import (
    IIdentificationLookup,
)
from src.modules.identification.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from src.modules.identification.domain.value_objects.ids import IdentificationId
from src.modules.training import (
    IdentificationOrigin,
    IdentificationSignals,
    SpeciesSuggestion,
    TrainingIdentificationSampleId,
)
from src.shared.domain import UserId


def make_identification(
    user_id: UserId | None = None,
    source: IdentificationOrigin = "consensus",
    scientific_name: str = "Monstera deliciosa",
) -> Identification:
    return Identification.create(
        user_id=user_id or UserId(uuid4()),
        training_sample_id=TrainingIdentificationSampleId(uuid4()),
        species_id=PlantSpeciesId(uuid4()),
        scientific_name=scientific_name,
        confidence=0.9,
        source=source,
        image_key="identifications/monstera.jpg",
        created_at=datetime.now(UTC),
    )


def make_result(
    scientific_name: str = "Monstera deliciosa",
    confidence: float = 0.9,
    genus: str | None = None,
    source: IdentificationOrigin = "consensus",
) -> IdentificationResult:
    return IdentificationResult(
        scientific_name=scientific_name,
        confidence=ConfidenceScore(confidence),
        source=source,
        family="Araceae",
        genus=genus,
        signals=(IdentificationSignals(
            provider="kindwise",
            suggestions=(SpeciesSuggestion(scientific_name, confidence),),
            is_plant_probability=0.99,
        ),),
    )


@dataclass
class StubPlantIdentifier(IPlantIdentifier):
    """Devolve `result` e guarda o que recebeu: (bytes da imagem, latitude, longitude)."""
    result: IdentificationResult = field(default_factory=make_result)
    calls: list[tuple[bytes, float | None, float | None]] = field(default_factory=list)

    async def identify(
        self, image_bytes: bytes, latitude: float | None = None, longitude: float | None = None,
    ) -> IdentificationResult:
        self.calls.append((image_bytes, latitude, longitude))
        return self.result


class InMemoryIdentificationRepository(IIdentificationRepository):
    def __init__(self, *identifications: Identification) -> None:
        self.by_id: dict[IdentificationId, Identification] = {i.id: i for i in identifications}

    async def save(self, identification: Identification) -> Identification:
        self.by_id[identification.id] = identification
        return identification

    async def get_for_user(self, identification_id: IdentificationId, user_id: UserId) -> Identification | None:
        found = self.by_id.get(identification_id)
        return found if found is not None and found.user_id == user_id else None


class FakeIdentificationUnitOfWork(IIdentificationUnitOfWork):
    """Identificações em memória (gravadas na hora, sem rollback), transações abertas e commits."""

    def __init__(self, identifications: InMemoryIdentificationRepository | None = None) -> None:
        self.identifications: InMemoryIdentificationRepository = identifications or InMemoryIdentificationRepository()
        self.opened = 0
        self.commits = 0

    @property
    def joined(self) -> bool:
        return False

    async def __aenter__(self) -> Self:
        self.opened += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakeIdentificationLookup(IIdentificationLookup):
    """As identificações dadas existem, cada uma só para o próprio dono."""

    def __init__(self, *identifications: Identification) -> None:
        self._repository = InMemoryIdentificationRepository(*identifications)

    async def get_for_user(self, identification_id: IdentificationId, user_id: UserId) -> Identification:
        identification = await self._repository.get_for_user(identification_id, user_id)
        if identification is None:
            raise IdentificationNotFoundError(identification_id)
        return identification
