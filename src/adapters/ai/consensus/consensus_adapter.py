import asyncio
import structlog
from src.domain.ports.plant_identifier import IPlantIdentifier, IdentificationResult, SimilarImage
from src.domain.policies.consensus_policy import ConsensusPolicy
from src.domain.value_objects.confidence_score import ConfidenceScore

log = structlog.get_logger()

_TIMEOUT_SECONDS = 10.0

class ConsensusIdentifier(IPlantIdentifier):
    def __init__(
        self,
        kindwise: IPlantIdentifier,
        plantnet: IPlantIdentifier,
    ) -> None:
        self._kindwise = kindwise
        self._plantnet = plantnet

    async def identify(
        self,
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        kindwise_result, plantnet_result = await asyncio.gather(
            self._call_with_timeout(self._kindwise, image_bytes, latitude, longitude, "kindwise"),
            self._call_with_timeout(self._plantnet, image_bytes, latitude, longitude, "plantnet"),
        )

        consensus = ConsensusPolicy.resolve(kindwise_result, plantnet_result)

        log.info(
            "consensus.resolved",
            scientific_name=consensus.scientific_name,
            reason=consensus.reason.value,
            source=consensus.source,
            confidence=consensus.confidence.value,
            low_confidence=consensus.low_confidence,
        )

        return IdentificationResult(
            scientific_name=consensus.scientific_name,
            confidence=consensus.confidence,
            source=consensus.source,
            provider_entity_id=consensus.provider_entity_id,
            gbif_id=consensus.gbif_id,
            family=consensus.family,
            genus=consensus.genus,
            common_names=consensus.common_names,
            low_confidence=consensus.low_confidence,
        )

    async def _call_with_timeout(
        self,
        identifier: IPlantIdentifier,
        image_bytes: bytes,
        latitude: float | None,
        longitude: float | None,
        source: str,
    ) -> IdentificationResult | None:
        try:
            return await asyncio.wait_for(
                identifier.identify(image_bytes, latitude=latitude, longitude=longitude),
                timeout=_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            log.warning("consensus.timeout", source=source)
            return None
        except Exception as e:
            log.warning("consensus.failed", source=source, error=str(e))
            return None