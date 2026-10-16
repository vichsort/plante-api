from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.value_objects.confidence_score import ConfidenceScore
from src.modules.catalog import ImageSource
from src.modules.training import IdentificationOrigin, IdentificationSignals


@dataclass(frozen=True)
class SimilarImage:
    url: str
    similarity: float
    source: ImageSource
    url_small: str | None = None
    license_name: str | None = None

@dataclass(frozen=True)
class IdentificationResult:
    scientific_name: str
    confidence: ConfidenceScore
    source: IdentificationOrigin
    provider_entity_id: str | None = None
    gbif_id: str | None = None
    family: str | None = None
    genus: str | None = None
    common_names: tuple[str, ...] = ()
    similar_images: tuple[SimilarImage, ...] = ()
    low_confidence: bool = False
    # O que cada provedor consultado disse (um no modo simples, os dois no consenso)
    signals: tuple[IdentificationSignals, ...] = ()

class IPlantIdentifier(ABC):
    @abstractmethod
    async def identify(
        self, 
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        """Identifica uma planta a partir de bytes de imagem."""
        ...