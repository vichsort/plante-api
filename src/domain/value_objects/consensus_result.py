from dataclasses import dataclass
from enum import StrEnum

from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.sources import (
    IdentificationOrigin,
    IdentificationProvider,
)


class ConsensusReason(StrEnum):
    EXACT_MATCH = "exact_match"           # scientific_name igual nas duas APIs
    GENUS_MATCH = "genus_match"           # genus igual, espécie diferente
    SINGLE_SOURCE = "single_source"       # uma API falhou, fallback para a outra
    KINDWISE_OVERRIDE = "kindwise_override"   # desacordo total, Kindwise venceu
    PLANTNET_OVERRIDE = "plantnet_override"   # desacordo total, PlantNet venceu por score muito maior

@dataclass(frozen=True)
class ConsensusResult:
    scientific_name: str
    confidence: ConfidenceScore
    reason: ConsensusReason
    low_confidence: bool
    source: IdentificationOrigin
    provider: IdentificationProvider      # provedor cujos dados foram usados
    family: str | None = None
    genus: str | None = None
    common_names: tuple[str, ...] = ()
    provider_entity_id: str | None = None
    gbif_id: str | None = None

    @property
    def is_consensus(self) -> bool:
        return self.reason in (ConsensusReason.EXACT_MATCH, ConsensusReason.GENUS_MATCH)