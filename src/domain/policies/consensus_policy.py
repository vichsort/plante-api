# src/domain/policies/consensus_policy.py
from src.domain.ports.plant_identifier import IdentificationResult
from src.domain.value_objects.consensus_result import ConsensusResult, ConsensusReason
from src.domain.value_objects.confidence_score import ConfidenceScore

_KINDWISE_WEIGHT = 0.60
_PLANTNET_WEIGHT = 0.40
_PLANTNET_OVERRIDE_THRESHOLD = 0.20


class ConsensusPolicy:

    @staticmethod
    def resolve(
        kindwise: IdentificationResult | None,
        plantnet: IdentificationResult | None,
    ) -> ConsensusResult:

        # Um falhou — fallback para o outro
        if kindwise is None and plantnet is not None:
            return ConsensusPolicy._from_single(plantnet, "plantnet", ConsensusReason.SINGLE_SOURCE)
        if plantnet is None and kindwise is not None:
            return ConsensusPolicy._from_single(kindwise, "kindwise", ConsensusReason.SINGLE_SOURCE)
        if kindwise is None and plantnet is None:
            raise ValueError("Both identifiers failed — cannot resolve consensus.")

        # Cenário A — acordo exato
        if kindwise.scientific_name == plantnet.scientific_name:
            score = (
                kindwise.confidence.value * _KINDWISE_WEIGHT
                + plantnet.confidence.value * _PLANTNET_WEIGHT
            )
            confidence = ConfidenceScore(score)
            return ConsensusResult(
                scientific_name=kindwise.scientific_name,
                confidence=confidence,
                reason=ConsensusReason.EXACT_MATCH,
                low_confidence=confidence.requires_human_review(),
                source="consensus",
                family=kindwise.family,
                genus=kindwise.genus,
                common_names=kindwise.common_names,
                provider_entity_id=kindwise.provider_entity_id,
                gbif_id=kindwise.gbif_id,
            )

        # Cenário B — acordo de gênero
        if kindwise.genus and plantnet.genus and kindwise.genus == plantnet.genus:
            winner = (
                kindwise if kindwise.confidence.value >= plantnet.confidence.value
                else plantnet
            )
            return ConsensusResult(
                scientific_name=winner.scientific_name,
                confidence=winner.confidence,
                reason=ConsensusReason.GENUS_MATCH,
                low_confidence=True,  # sempre low_confidence no acordo parcial
                source="consensus_partial",
                family=winner.family,
                genus=winner.genus,
                common_names=winner.common_names,
                provider_entity_id=winner.provider_entity_id,
                gbif_id=winner.gbif_id,
            )

        # Cenário C — desacordo total
        plantnet_dominates = (
            plantnet.confidence.value - kindwise.confidence.value >= _PLANTNET_OVERRIDE_THRESHOLD
        )
        if plantnet_dominates:
            winner = plantnet
            reason = ConsensusReason.PLANTNET_OVERRIDE
            source = "plantnet"
        else:
            winner = kindwise
            reason = ConsensusReason.KINDWISE_OVERRIDE
            source = "kindwise"

        return ConsensusResult(
            scientific_name=winner.scientific_name,
            confidence=winner.confidence,
            reason=reason,
            low_confidence=True,  # desacordo total é sempre low_confidence
            source=source,
            family=winner.family,
            genus=winner.genus,
            common_names=winner.common_names,
            provider_entity_id=winner.provider_entity_id,
            gbif_id=winner.gbif_id,
        )

    @staticmethod
    def _from_single(
        result: IdentificationResult,
        source: str,
        reason: ConsensusReason,
    ) -> ConsensusResult:
        return ConsensusResult(
            scientific_name=result.scientific_name,
            confidence=result.confidence,
            reason=reason,
            low_confidence=result.confidence.requires_human_review(),
            source=source,
            family=result.family,
            genus=result.genus,
            common_names=result.common_names,
            provider_entity_id=result.provider_entity_id,
            gbif_id=result.gbif_id,
        )