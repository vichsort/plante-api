from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class SimilarImage:
    url: str
    similarity: float
    url_small: str | None = None
    license_name: str | None = None

@dataclass(frozen=True)
class IdentificationResult:
    scientific_name: str
    confidence: float
    source: str
    kindwise_entity_id: str | None = None
    gbif_id: str | None = None
    family: str | None = None
    genus: str | None = None
    common_names: tuple[str, ...] = ()
    similar_images: tuple[SimilarImage, ...] = ()

class IPlantIdentifier(ABC):
    @abstractmethod
    async def identify(self, image_bytes: bytes) -> IdentificationResult:
        """Identifica uma planta a partir de bytes de imagem."""
        ...

    @abstractmethod
    async def search_by_name(self, scientific_name: str) -> IdentificationResult | None:
        """Busca dados de uma espécie pelo nome científico."""
        ...