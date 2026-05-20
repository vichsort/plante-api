from abc import ABC, abstractmethod
from dataclasses import dataclass
from src.domain.value_objects.confidence_score import ConfidenceScore

@dataclass(frozen=True)
class SimilarImage:
    url: str
    similarity: float
    url_small: str | None = None
    license_name: str | None = None

@dataclass(frozen=True)
class IdentificationResult:
    scientific_name: str
    confidence: ConfidenceScore
    source: str
    provider_entity_id: str | None = None # kindwise | plantnet
    gbif_id: str | None = None
    family: str | None = None
    genus: str | None = None
    common_names: tuple[str, ...] = ()
    similar_images: tuple[SimilarImage, ...] = ()

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